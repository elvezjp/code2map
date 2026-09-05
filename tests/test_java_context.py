"""Regressions for Java source coverage and context after structural splitting."""

import json
from pathlib import Path

from code2map import build_index, pack_index, validate_pack
from code2map.context.model import canonical


def index_java(tmp_path, text):
    source = tmp_path / "Example.java"
    source.write_bytes(text.encode("utf-8"))
    return build_index(source)


def test_unicode_crlf_overloads_and_repeatability(tmp_path):
    text = """// 日本語😀\r
class Example {\r
    int 値 = 1;\r
    int helper(int x) { return x; }\r
    int helper(String x) { return x.length(); }\r
    int run(int 入力) { return helper(入力) + 値; }\r
}\r
"""
    index = index_java(tmp_path, text)
    assert canonical(index) == canonical(build_index(tmp_path))
    assert "tree-sitter=" in index["adapters"]["java-tree-sitter"]
    calls = [
        e for e in index["edges"] if e["kind"] == "call" and e["symbol"] == "helper"
    ]
    assert len(calls) == 1
    assert calls[0]["resolution"] == "ambiguous"
    assert len(calls[0]["target_ids"]) == 2
    assert any(
        n["kind"] == "parameter" and n["symbol"] == "入力" for n in index["nodes"]
    )
    for budget in [1, 2500, 8000, 100000]:
        packed = pack_index(index, budget=budget)
        assert validate_pack(index, packed)["coverage"] == "exactly-once"
        recovered = "".join(
            json.loads(p["payload"])["target"]["text"] for p in packed["packets"]
        )
        assert recovered == text


def test_java_split_keeps_else_guard_loop_header_and_handlers(tmp_path):
    statements = "\n".join(f"consume({i});" for i in range(120))
    text = (
        """class Example {
    void run(boolean enabled) {
        try {
            if (enabled) { consume(0); } else {
                for (int i = 0; i < 120; i++) {
"""
        + statements
        + """
                }
            }
        } catch (Exception e) { report(e); }
        finally { cleanup(); }
    }
}"""
    )
    index = index_java(tmp_path, text)
    packed = pack_index(index, budget=7000)
    assert packed["summary"]["ready"] > 1
    marker = text.index("consume(77)")
    packet = next(p for p in packed["packets"] if p["start"] <= marker < p["end"])
    payload = json.loads(packet["payload"])
    headers = "\n".join(c["text"] for c in payload["enclosing_context"])
    assert "if (enabled)" in headers
    assert "else" in headers
    assert "i < 120" in headers
    assert len(payload["exception_regions"]) == 2


def test_java_switch_and_nested_types(tmp_path):
    text = """record Example(int value) {
        static class Nested { void method() {} }
        int run(int x) { return switch (x) { case 1 -> 2; default -> 3; }; }
        void traditional(int x) { switch(x) { case 1: run(x); break; default: break; } }
    }"""
    index = index_java(tmp_path, text)
    assert not index["diagnostics"]
    assert {"Example", "Nested"} <= {
        n["symbol"] for n in index["nodes"] if n["kind"] == "class"
    }
    assert any(n["kind"] == "branch" for n in index["nodes"])
    validate_pack(index, pack_index(index, budget=2000))


def test_do_while_remains_indivisible_to_retain_trailing_condition(tmp_path):
    body = "\n".join("consume(1);" for _ in range(100))
    text = "class Example { void run() { do { " + body + " } while (ready()); } }"
    index = index_java(tmp_path, text)
    do_node = next(n for n in index["nodes"] if n["name"] == "do_statement")
    assert not any(n["parent_id"] == do_node["id"] for n in index["nodes"])
    packed = pack_index(index, budget=1000)
    assert any(
        p["status"] == "oversized"
        and p["start"] <= do_node["start"]
        and p["end"] >= do_node["end"]
        for p in packed["packets"]
    )


def test_java_syntax_error_is_visible_and_source_is_retained(tmp_path):
    text = "class Example { void broken( { return; }"
    index = index_java(tmp_path, text)
    assert index["diagnostics"][0]["code"] == "JAVA_PARSE_ERROR"
    packed = pack_index(index)
    assert packed["summary"]["opaque"] == 1
    assert json.loads(packed["packets"][0]["payload"])["target"]["text"] == text


def test_mixed_language_directory(tmp_path):
    (tmp_path / "Example.java").write_text("class Example { void run() {} }")
    (tmp_path / "example.py").write_text("def run():\n    pass\n")
    (tmp_path / "example.sql").write_text("BEGIN NULL; END;\n/\n")
    index = build_index(tmp_path)
    assert len(index["sources"]) == 3
    validate_pack(index, pack_index(index, budget=3000))


def test_all_legacy_java_fixtures_are_indexable():
    fixtures = Path(__file__).parent / "fixtures"
    from code2map.context.adapters.java import JavaAdapter

    index = build_index(fixtures, adapters=[JavaAdapter()])
    validate_pack(index, pack_index(index, budget=16000))
