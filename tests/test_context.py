import copy
import json
from pathlib import Path
import tempfile
import unittest

from code2map import build_index, pack_index, validate_index, validate_pack
from code2map.context.model import Node, Parsed, canonical, digest


ROOT = Path(__file__).resolve().parents[1]


class MapTest(unittest.TestCase):
    def index_text(self, text, suffix=".sql", encoding="utf-8"):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ("source" + suffix)
            p.write_bytes(text.encode(encoding))
            return build_index(p, encoding=encoding)

    def test_plsql_entire_package_and_initialization(self):
        i = build_index(ROOT / "examples/accounting.sql")
        kinds = [n["kind"] for n in i["nodes"]]
        self.assertIn("package_spec", kinds)
        self.assertIn("package_body", kinds)
        self.assertIn("initialization", kinds)
        self.assertIn("exception", kinds)
        self.assertEqual(
            kinds.count("function"), 1
        )  # forward declaration is not a body
        self.assertFalse(i["diagnostics"])
        self.assertTrue(
            any(
                e["symbol"] == "ADJUSTED"
                and e["resolution"] == "candidate"
                and e["kind"] == "call"
                for e in i["edges"]
            )
        )
        self.assertTrue(
            any(e["symbol"] == "G_TOTAL" and e["target_ids"] for e in i["edges"])
        )

    def test_byte_identical_outputs_and_portable_paths(self):
        text = "CREATE PROCEDURE p IS BEGIN NULL; END;\n/\n"
        a = self.index_text(text)
        b = self.index_text(text)
        self.assertEqual(canonical(a), canonical(b))
        self.assertEqual(canonical(pack_index(a)), canonical(pack_index(b)))
        self.assertEqual(a["sources"][0]["path"], "source.sql")

    def test_coverage_all_budgets_and_exact_crlf_unicode(self):
        text = (
            "-- 日本語\r\nCREATE PROCEDURE p IS\r\nBEGIN\r\n"
            + "  NULL;\r\n" * 100
            + "END;\r\n/\r\n"
        )
        i = self.index_text(text, encoding="cp932")
        self.assertEqual(i["sources"][0]["text"], text)
        for budget in (500, 1800, 3000, 8000, 20000):
            p = pack_index(i, budget=budget, reserve=100)
            validate_pack(i, p)
            restored = "".join(
                json.loads(c["payload"])["target"]["text"] for c in p["packets"]
            )
            self.assertEqual(restored, text)
            for packet in p["packets"]:
                if packet["status"] == "ready":
                    self.assertLessEqual(
                        len(packet["payload"].encode("utf-8")), budget - 100
                    )

    def test_split_preserves_enclosing_guards_and_else(self):
        text = (
            "BEGIN\nFOR i IN 1..10 LOOP\nIF i > 5 THEN\n"
            + "NULL;\n" * 500
            + "ELSE\n"
            + "NULL;\n" * 500
            + "END IF;\nEND LOOP;\nEND;\n/"
        )
        i = self.index_text(text)
        p = pack_index(i, budget=2600)
        self.assertGreater(len(p["packets"]), 2)
        found_else = False
        for packet in p["packets"]:
            body = json.loads(packet["payload"])
            contexts = body["enclosing_context"]
            if any(c["name"] == "ELSE" for c in contexts):
                found_else = True
                self.assertTrue(any("IF i > 5 THEN" in c["text"] for c in contexts))
                self.assertTrue(
                    any("FOR i IN 1..10 LOOP" in c["text"] for c in contexts)
                )
        self.assertTrue(found_else)

    def test_quoted_identifiers_and_literals_do_not_create_blocks(self):
        text = """CREATE PROCEDURE "Mixed" IS
v VARCHAR2(100) := q'[END; / IF THEN]';
BEGIN
  /* BEGIN END; */
  v := 'it''s END IF;';
  "Mixed"();
END "Mixed";
/
"""
        i = self.index_text(text)
        self.assertFalse(i["diagnostics"])
        self.assertEqual(sum(n["kind"] == "procedure" for n in i["nodes"]), 1)
        self.assertTrue(
            any(
                e["symbol"] == '"Mixed"' and e["kind"] == "call" and e["target_ids"]
                for e in i["edges"]
            )
        )

    def test_sql_case_expression_and_procedural_case(self):
        i = self.index_text("""BEGIN
IF CASE WHEN 1=1 THEN 1 ELSE 0 END = 1 THEN NULL; END IF;
CASE v WHEN 1 THEN NULL; WHEN 2 THEN NULL; ELSE NULL; END CASE;
SELECT CASE WHEN x=1 THEN 'x' ELSE 'y' END INTO v FROM t;
END;
/
""")
        self.assertFalse(i["diagnostics"])
        self.assertEqual(sum(n["kind"] == "control" for n in i["nodes"]), 2)

    def test_unrecognized_source_retained_as_opaque(self):
        for text in ("BEGIN NULL; END IF;", "BEGIN NULL;", "BEGIN x := q'[oops;"):
            i = self.index_text(text)
            self.assertTrue(i["diagnostics"])
            p = pack_index(i, budget=10000)
            self.assertEqual(p["packets"][0]["status"], "opaque")
            self.assertEqual(
                json.loads(p["packets"][0]["payload"])["target"]["text"], text
            )

    def test_oversized_sql_is_not_cut(self):
        text = "BEGIN\nSELECT '" + "x" * 10000 + "' INTO v FROM dual;\nEND;\n/"
        i = self.index_text(text)
        p = pack_index(i, budget=3000)
        big = [x for x in p["packets"] if x["status"] == "oversized"]
        self.assertTrue(big)
        self.assertTrue(
            any(
                "SELECT '" in json.loads(x["payload"])["target"]["text"]
                and "FROM dual;" in json.loads(x["payload"])["target"]["text"]
                for x in big
            )
        )

    def test_cross_file_calls_and_ambiguous_overloads(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "a.sql").write_text(
                "CREATE PROCEDURE a IS BEGIN pkg.b(); END;\n/", encoding="utf-8"
            )
            (p / "b.sql").write_text(
                "CREATE PACKAGE BODY pkg AS PROCEDURE b IS BEGIN NULL; END; END;\n/",
                encoding="utf-8",
            )
            i = build_index(p)
            call = next(e for e in i["edges"] if e["symbol"] == "PKG.B")
            self.assertEqual(call["resolution"], "candidate")
            packed = pack_index(i, budget=12000)
            caller = next(
                json.loads(x["payload"])
                for x in packed["packets"]
                if json.loads(x["payload"])["target"]["path"] == "a.sql"
            )
            self.assertTrue(
                any(c["path"] == "b.sql" for c in caller["dependency_context"])
            )
            (p / "c.sql").write_text((p / "b.sql").read_text(), encoding="utf-8")
            i = build_index(p)
            self.assertEqual(
                next(e for e in i["edges"] if e["symbol"] == "PKG.B")["resolution"],
                "ambiguous",
            )

    def test_unresolved_call_and_goto_survive_pack(self):
        i = self.index_text(
            "BEGIN external_pkg.work(); GOTO done; <<done>> NULL; END;\n/"
        )
        self.assertFalse(i["diagnostics"])
        self.assertTrue(
            any(
                e["symbol"] == "EXTERNAL_PKG.WORK" and e["resolution"] == "unresolved"
                for e in i["edges"]
            )
        )
        self.assertTrue(
            any(e["kind"] == "jump" and e["target_ids"] for e in i["edges"])
        )

    def test_package_body_references_public_spec_declaration(self):
        text = "CREATE PACKAGE p AS g NUMBER; END;\n/\nCREATE PACKAGE BODY p AS PROCEDURE f IS BEGIN g := 1; END; END;\n/"
        i = self.index_text(text)
        edge = next(e for e in i["edges"] if e["symbol"] == "G")
        self.assertEqual(edge["resolution"], "candidate")
        node = next(n for n in i["nodes"] if n["id"] == edge["target_ids"][0])
        parent = next(n for n in i["nodes"] if n["id"] == node["parent_id"])
        self.assertEqual(parent["kind"], "package_spec")

    def test_dot_inside_quoted_local_name_is_not_qualification(self):
        i = self.index_text(
            'CREATE PROCEDURE p IS "a.b" NUMBER; BEGIN "a.b" := 1; END;\n/'
        )
        self.assertTrue(
            any(
                e["symbol"] == '"a.b"' and e["resolution"] == "candidate"
                for e in i["edges"]
            )
        )

    def test_python_unicode_parameters_nested_scopes(self):
        text = "税率 = 1.1\n\ndef outer(金額):\n    def inner(x):\n        return x * 税率\n    return inner(金額)\n"
        i = self.index_text(text, suffix=".py")
        self.assertFalse(i["diagnostics"])
        self.assertTrue(
            any(n["symbol"] == "金額" and n["kind"] == "parameter" for n in i["nodes"])
        )
        self.assertTrue(
            any(e["symbol"] == "inner" and e["target_ids"] for e in i["edges"])
        )
        validate_pack(i, pack_index(i, budget=3000))

    def test_python_else_finally_match_decorators(self):
        text = """@decorator
def f(x):
    try:
        if x:
            pass
        elif x == 2:
            pass
        else:
            pass
    except ValueError:
        pass
    else:
        pass
    finally:
        pass
    match x:
        case 1:
            pass
        case _:
            pass
"""
        i = self.index_text(text, suffix=".py")
        self.assertFalse(i["diagnostics"])
        self.assertTrue(
            any(n["kind"] == "branch" and n["name"] == "finally" for n in i["nodes"])
        )
        for budget in (2000, 6000):
            validate_pack(i, pack_index(i, budget=budget))

    def test_python_parse_error_not_silently_skipped(self):
        i = self.index_text("def x(:", suffix=".py")
        self.assertTrue(i["diagnostics"])
        self.assertEqual(pack_index(i)["summary"]["opaque"], 1)

    def test_optional_context_omissions_are_visible(self):
        i = build_index(ROOT / "examples/pricing.py")
        p = pack_index(i, budget=2600, dependency_limit=0)
        self.assertTrue(any(x["omitted_context"] for x in p["packets"]))

    def test_custom_counter_and_reserve(self):
        class Characters:
            identity = "unicode-characters-test-v1"

            def count(self, text):
                return len(text)

        i = self.index_text("BEGIN NULL; END;\n/")
        p = pack_index(i, budget=2000, reserve=100, counter=Characters())
        validate_pack(i, p, counter=Characters())
        with self.assertRaises(ValueError):
            validate_pack(i, p)

    def test_adapter_extension_point_and_contract_rejection(self):
        class Plain:
            name, version, extensions = "plain-test", "1", (".demo",)

            def parse(self, text, path):
                return Parsed(
                    Node(
                        "file",
                        0,
                        len(text),
                        path,
                        0,
                        children=[Node("statement", 0, len(text))],
                    )
                )

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x.demo"
            path.write_text("test")
            i = build_index(path, adapters=[Plain()])
            self.assertEqual(i["adapters"], {"plain-test": "1"})
            with self.assertRaises(ValueError):
                build_index(path, adapters=[Plain(), Plain()])

    def test_index_and_payload_tampering_detected(self):
        i = self.index_text("BEGIN NULL; END;\n/")
        broken = copy.deepcopy(i)
        broken["sources"][0]["text"] += "x"
        with self.assertRaises(ValueError):
            validate_index(broken)
        p = pack_index(i)
        broken = copy.deepcopy(p)
        body = json.loads(broken["packets"][0]["payload"])
        body["target"]["text"] = "tampered"
        broken["packets"][0]["payload"] = canonical(body)
        broken["packets"][0]["payload_sha256"] = digest(canonical(body))
        with self.assertRaises(ValueError):
            validate_pack(i, broken)

    def test_coverage_gap_and_budget_tampering_detected(self):
        i = self.index_text("BEGIN NULL; END;\n/")
        p = pack_index(i)
        p["packets"][0]["start"] = 1
        with self.assertRaises(ValueError):
            validate_pack(i, p)
        p = pack_index(i)
        p["packets"][0]["budget_used"] = 1
        with self.assertRaises(ValueError):
            validate_pack(i, p)

    def test_mandatory_context_and_relations_cannot_be_removed(self):
        text = (
            "def f():\n    try:\n        external()\n"
            + "        pass\n" * 400
            + "    except Exception:\n        pass\n"
        )
        i = self.index_text(text, suffix=".py")
        packed = pack_index(i, budget=2600)
        for field in ("enclosing_context", "relations", "exception_regions"):
            p = copy.deepcopy(packed)
            changed = False
            for packet in p["packets"]:
                body = json.loads(packet["payload"])
                if body[field]:
                    body[field] = []
                    packet["payload"] = canonical(body)
                    packet["payload_sha256"] = digest(packet["payload"])
                    packet["budget_used"] = len(packet["payload"].encode("utf-8"))
                    changed = True
                    break
            self.assertTrue(changed, field)
            with self.assertRaises(ValueError):
                validate_pack(i, p)

    def test_sibling_overlap_from_custom_adapter_is_rejected(self):
        class Broken:
            name, version, extensions = "broken", "1", (".broken",)

            def parse(self, text, path):
                return Parsed(
                    Node(
                        "file",
                        0,
                        len(text),
                        path,
                        0,
                        children=[Node("statement", 0, 3), Node("statement", 2, 4)],
                    )
                )

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.broken"
            p.write_text("1234")
            with self.assertRaisesRegex(ValueError, "overlapping siblings"):
                build_index(p, adapters=[Broken()])

    def test_empty_file_and_comment_only(self):
        for text in ("", "-- empty\n", "/* only comment */"):
            i = self.index_text(text)
            validate_pack(i, pack_index(i))

    def test_invalid_configuration_and_unsupported_input(self):
        i = self.index_text("BEGIN NULL; END;")
        for kwargs in (
            {"budget": 0},
            {"budget": 100, "reserve": 100},
            {"dependency_limit": -1},
        ):
            with self.assertRaises(ValueError):
                pack_index(i, **kwargs)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                build_index(td)

    def test_cli_roundtrip_and_source_overwrite_refusal(self):
        from code2map.cli import main

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "x.sql"
            source.write_text("BEGIN NULL; END;\n/")
            before = source.read_bytes()
            self.assertEqual(main(["index", str(source), "--output", str(source)]), 2)
            self.assertEqual(source.read_bytes(), before)
            index = root / "index.json"
            packed = root / "pack.json"
            self.assertEqual(main(["index", str(source), "--output", str(index)]), 0)
            self.assertEqual(main(["pack", str(index), "--output", str(packed)]), 0)
            self.assertEqual(main(["check", str(index), "--pack", str(packed)]), 0)
            self.assertEqual(main(["pack", str(index), "--output", str(index)]), 2)


if __name__ == "__main__":
    unittest.main()
