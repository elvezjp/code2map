"""No LLM, network, database access, or source execution."""

import json
import sys
from pathlib import Path
from .index import build_index, validate_index
from .packing import pack_index, validate_pack
from .model import canonical


def add_commands(sub):
    """Register context commands on the shared public CLI parser."""
    index = sub.add_parser("index", help="snapshot and structure supported sources")
    index.add_argument("input")
    index.add_argument("--output", required=True)
    index.add_argument(
        "--encoding",
        default="utf-8",
        choices=["utf-8", "utf-8-sig", "cp932", "shift_jis", "euc_jp"],
    )
    pack = sub.add_parser(
        "pack", help="partition a locked index; budget units are UTF-8 bytes"
    )
    pack.add_argument("index")
    pack.add_argument("--output", required=True)
    pack.add_argument("--budget-bytes", type=int, default=16000)
    pack.add_argument("--reserve-bytes", type=int, default=0)
    pack.add_argument("--dependency-limit", type=int, default=8)
    check = sub.add_parser(
        "check", help="validate index, optional pack coverage and budgets"
    )
    check.add_argument("index")
    check.add_argument("--pack")
    show = sub.add_parser(
        "show", help="retrieve a node's original source from a locked index"
    )
    show.add_argument("index")
    show.add_argument("node_id")
    tree = sub.add_parser(
        "tree", help="show source hierarchy without dumping source text"
    )
    tree.add_argument("index")
    tree.add_argument("--depth", type=int, default=3)


def run(args):
    """Run a parsed context command; return its process exit code."""
    try:
        if args.command == "index":
            result = build_index(args.input, encoding=args.encoding)
            # Refuse accidental replacement of any source in this snapshot.
            base = Path(args.input).resolve()
            base = base if base.is_dir() else base.parent
            output = Path(args.output).resolve()
            if output in {base / s["path"] for s in result["sources"]}:
                raise ValueError("output must not overwrite a source")
        else:
            result = json.loads(Path(args.index).read_text(encoding="utf-8"))
            validate_index(result)
            if args.command == "tree":
                if args.depth < 0:
                    raise ValueError("depth must be nonnegative")
                depths = {}
                for node in result["nodes"]:
                    depth = depths.get(node["parent_id"], -1) + 1
                    depths[node["id"]] = depth
                    if depth <= args.depth:
                        print(
                            "  " * depth
                            + f"{node['kind']} {node['name']} L{node['start_line']}-{node['end_line']} [{node['confidence']}] {node['id']}"
                        )
                return 0
            if args.command == "check":
                checked = (
                    validate_pack(
                        result, json.loads(Path(args.pack).read_text(encoding="utf-8"))
                    )
                    if args.pack
                    else validate_index(result)
                )
                print(canonical(checked), end="")
                return 0
            if args.command == "show":
                node = next(
                    (n for n in result["nodes"] if n["id"] == args.node_id), None
                )
                if node is None:
                    raise ValueError("node not found")
                source = next(
                    s for s in result["sources"] if s["id"] == node["source_id"]
                )
                print(
                    f"{source['path']}:{node['start_line']} ({node['kind']}, {node['confidence']})"
                )
                print(source["text"][node["start"] : node["end"]])
                return 0
            if Path(args.output).resolve() == Path(args.index).resolve():
                raise ValueError("pack output must not overwrite the index")
            result = pack_index(
                result,
                budget=args.budget_bytes,
                reserve=args.reserve_bytes,
                dependency_limit=args.dependency_limit,
            )
            output = Path(args.output).resolve()
        if output.suffix.lower() != ".json":
            raise ValueError("output must end in .json")
        output.parent.mkdir(parents=True, exist_ok=True)
        # A temporary neighbor plus replace avoids a partial JSON on write failure.
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=output.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            try:
                handle.write(canonical(result))
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
        try:
            os.replace(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)
        print(str(output))
        if args.command == "pack":
            print(canonical(result["summary"]), end="")
            return (
                3
                if result["summary"]["oversized"] or result["summary"]["opaque"]
                else 0
            )
        return 3 if result["diagnostics"] else 0
    except (OSError, ValueError, KeyError, TypeError, LookupError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
