"""Regressions for C# source coverage and context after structural splitting."""

import json

from code2map import build_index, pack_index, validate_pack
from code2map.context.model import canonical


def index_csharp(tmp_path, text, name="Example.cs"):
    source = tmp_path / name
    source.write_bytes(text.encode("utf-8"))
    return build_index(source)


def recovered(index, packed):
    return "".join(json.loads(p["payload"])["target"]["text"] for p in packed["packets"])


def test_unicode_crlf_overloads_and_repeatability(tmp_path):
    text = """// 日本語😀\r
namespace Demo\r
{\r
    class Example\r
    {\r
        int 値 = 1;\r
        int Helper(int x) { return x; }\r
        int Helper(string x) { return x.Length; }\r
        int Run(int 入力) { return Helper(入力) + 値; }\r
    }\r
}\r
"""
    index = index_csharp(tmp_path, text)
    assert canonical(index) == canonical(build_index(tmp_path))
    assert "c-sharp=" in index["adapters"]["csharp-tree-sitter"]
    calls = [e for e in index["edges"] if e["kind"] == "call" and e["symbol"] == "Helper"]
    assert len(calls) == 1
    assert calls[0]["resolution"] == "ambiguous"
    assert len(calls[0]["target_ids"]) == 2
    assert any(n["kind"] == "parameter" and n["symbol"] == "入力" for n in index["nodes"])
    assert any(n["kind"] == "namespace" and n["symbol"] == "Demo" for n in index["nodes"])
    for budget in [1, 2500, 8000, 100000]:
        packed = pack_index(index, budget=budget)
        assert validate_pack(index, packed)["coverage"] == "exactly-once"
        assert recovered(index, packed) == text


def test_csharp_split_keeps_else_guard_loop_header_and_handlers(tmp_path):
    statements = "\n".join(f"Consume({i});" for i in range(120))
    text = (
        """class Example
{
    void Run(bool enabled)
    {
        try
        {
            if (enabled) { Consume(0); } else
            {
                for (int i = 0; i < 120; i++)
                {
"""
        + statements
        + """
                }
            }
        }
        catch (Exception e) { Report(e); }
        finally { Cleanup(); }
    }
}"""
    )
    index = index_csharp(tmp_path, text)
    packed = pack_index(index, budget=7000)
    assert packed["summary"]["ready"] > 1
    marker = text.index("Consume(77)")
    packet = next(p for p in packed["packets"] if p["start"] <= marker < p["end"])
    payload = json.loads(packet["payload"])
    headers = "\n".join(c["text"] for c in payload["enclosing_context"])
    assert "if (enabled)" in headers
    assert "else" in headers
    assert "i < 120" in headers
    assert len(payload["exception_regions"]) == 2
    assert recovered(index, packed) == text


def test_csharp_switch_nested_types_and_expression_bodies(tmp_path):
    text = """record Example(int Value)
{
    class Nested { void Method() {} }
    int Run(int x) => x switch { 1 => 2, _ => 3 };
    int Doubled => Value * 2;
    void Traditional(int x) { switch (x) { case 1: Run(x); break; default: break; } }
}"""
    index = index_csharp(tmp_path, text)
    assert not index["diagnostics"]
    assert {"Example", "Nested"} <= {n["symbol"] for n in index["nodes"] if n["kind"] == "class"}
    assert {"Run", "Doubled", "Traditional", "Method"} <= {
        n["symbol"] for n in index["nodes"] if n["kind"] == "function"
    }
    assert any(n["kind"] == "branch" for n in index["nodes"])
    # An expression-bodied member has its arrow clause as the body, not a block,
    # but a switch expression inside it still splits along its arms.
    run = next(n for n in index["nodes"] if n["symbol"] == "Run")
    run_children = [n for n in index["nodes"] if n["parent_id"] == run["id"]]
    assert not any(n["kind"] == "block" for n in run_children)
    switch = next(n for n in run_children if n["name"] == "switch_expression")
    assert sum(1 for n in index["nodes"] if n["parent_id"] == switch["id"] and n["kind"] == "branch") == 2
    validate_pack(index, pack_index(index, budget=2000))


def test_large_switch_expression_in_expression_bodied_member_splits(tmp_path):
    arms = ",\n".join(f"        {i} => Consume({i})" for i in range(150))
    text = "class Example\n{\n    int Run(int x) => x switch\n    {\n" + arms + ",\n        _ => 0\n    };\n}\n"
    index = index_csharp(tmp_path, text)
    packed = pack_index(index, budget=4000)
    assert packed["summary"]["oversized"] == 0
    assert packed["summary"]["ready"] > 1
    assert recovered(index, packed) == text


def test_conditional_compilation_keeps_inner_structure(tmp_path):
    consume = "\n".join(f"        Consume({i});" for i in range(120))
    text = (
        "#if DEBUG\nclass A\n{\n    void M()\n    {\n" + consume + "\n    }\n}\n"
        "#elif TRACE\nclass C { }\n#else\nclass B { void N() { } }\n#endif\nclass D { }\n"
    )
    index = index_csharp(tmp_path, text)
    assert not index["diagnostics"]
    classes = {n["symbol"] for n in index["nodes"] if n["kind"] == "class"}
    assert classes == {"A", "B", "C", "D"}
    assert {"M", "N"} <= {n["symbol"] for n in index["nodes"] if n["kind"] == "function"}
    names = [n["name"] for n in index["nodes"] if n["kind"] == "preproc"]
    assert names == ["#if DEBUG", "#elif TRACE", "#else"]
    packed = pack_index(index, budget=6000)
    assert packed["summary"]["oversized"] == 0
    marker = text.index("Consume(77)")
    packet = next(p for p in packed["packets"] if p["start"] <= marker < p["end"])
    headers = "\n".join(c["text"] for c in json.loads(packet["payload"])["enclosing_context"])
    assert "#if DEBUG" in headers
    assert "void M()" in headers
    assert recovered(index, packed) == text


def test_shared_case_labels_stay_in_one_branch_header(tmp_path):
    consume = "\n".join(f"                Consume({i});" for i in range(120))
    text = (
        "class Example\n{\n    void Run(int x)\n    {\n        switch (x)\n        {\n"
        "            case 1:\n            case 2:\n" + consume + "\n                break;\n"
        "            default:\n                break;\n        }\n    }\n}\n"
    )
    index = index_csharp(tmp_path, text)
    branches = [n for n in index["nodes"] if n["kind"] == "branch"]
    assert len(branches) == 2  # `case 1: case 2:` share one branch; `default:` is the other
    shared = min(branches, key=lambda n: n["start"])
    assert text[shared["start"] : shared["header_end"]].count("case") == 2
    packed = pack_index(index, budget=6000)
    marker = text.index("Consume(77)")
    packet = next(p for p in packed["packets"] if p["start"] <= marker < p["end"])
    assert packet["status"] == "ready"
    headers = "\n".join(c["text"] for c in json.loads(packet["payload"])["enclosing_context"])
    assert "case 1:" in headers and "case 2:" in headers
    assert recovered(index, packed) == text


def test_do_while_remains_indivisible_to_retain_trailing_condition(tmp_path):
    body = "\n".join("Consume(1);" for _ in range(100))
    text = "class Example { void Run() { do { " + body + " } while (Ready()); } }"
    index = index_csharp(tmp_path, text)
    do_node = next(n for n in index["nodes"] if n["name"] == "do_statement")
    assert not any(n["parent_id"] == do_node["id"] for n in index["nodes"])
    packed = pack_index(index, budget=1000)
    assert any(
        p["status"] == "oversized"
        and p["start"] <= do_node["start"]
        and p["end"] >= do_node["end"]
        for p in packed["packets"]
    )


def test_csharp_syntax_error_is_visible_and_source_is_retained(tmp_path):
    text = "class Example { void Broken( { return; } }"
    index = index_csharp(tmp_path, text)
    assert index["diagnostics"][0]["code"] == "CSHARP_PARSE_ERROR"
    packed = pack_index(index)
    assert packed["summary"]["opaque"] == 1
    assert json.loads(packed["packets"][0]["payload"])["target"]["text"] == text


def test_file_scoped_namespace_regions_locals_and_goto(tmp_path):
    text = """﻿using System;
namespace Demo.App;
#region Types
public class Calc
{
    public int Count { get { return _count; } set { _count = value; } }
    private int _count;
    public int Add(int x)
    {
        int Local(int q) { return q + 1; }
        retry: _count += x;
        if (_count < 0) goto retry;
        return Local(_count);
    }
}
#endregion
"""
    index = index_csharp(tmp_path, text)
    assert not index["diagnostics"]
    kinds = {n["name"]: n["kind"] for n in index["nodes"]}
    assert kinds["#region Types"] == "preproc"
    assert kinds["#endregion"] == "preproc"
    assert kinds["namespace Demo.App"] == "import"
    assert not any(n["kind"] == "namespace" for n in index["nodes"])
    assert {"Count", "Add", "Local"} <= {n["symbol"] for n in index["nodes"] if n["kind"] == "function"}
    assert any(n["kind"] == "branch" and n["name"] == "get" for n in index["nodes"])
    jump = next(e for e in index["edges"] if e["kind"] == "jump")
    assert jump["symbol"] == "retry" and jump["resolution"] == "candidate"
    local = next(e for e in index["edges"] if e["kind"] == "call" and e["symbol"] == "Local")
    assert local["resolution"] == "candidate"
    for budget in [1, 1200, 100000]:
        packed = pack_index(index, budget=budget)
        assert validate_pack(index, packed)["coverage"] == "exactly-once"
        assert recovered(index, packed) == text


def test_partial_classes_stay_separate_nodes(tmp_path):
    (tmp_path / "Part1.cs").write_text("partial class Example { void A() { B(); } }")
    (tmp_path / "Part2.cs").write_text("partial class Example { void B() {} }")
    index = build_index(tmp_path)
    classes = [n for n in index["nodes"] if n["kind"] == "class" and n["symbol"] == "Example"]
    assert len(classes) == 2
    call = next(e for e in index["edges"] if e["kind"] == "call" and e["symbol"] == "B")
    assert call["resolution"] == "unresolved"  # no cross-file binding is invented
    validate_pack(index, pack_index(index, budget=3000))


def test_mixed_language_directory_includes_csharp(tmp_path):
    (tmp_path / "Example.java").write_text("class Example { void run() {} }")
    (tmp_path / "Example.cs").write_text("class Example { void Run() {} }")
    (tmp_path / "example.py").write_text("def run():\n    pass\n")
    (tmp_path / "example.sql").write_text("BEGIN NULL; END;\n/\n")
    index = build_index(tmp_path)
    assert len(index["sources"]) == 4
    assert set(index["adapters"]) >= {"csharp-tree-sitter", "java-tree-sitter"}
    validate_pack(index, pack_index(index, budget=3000))
