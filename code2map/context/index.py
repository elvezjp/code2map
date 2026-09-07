"""Build a portable snapshot; resolve lexical candidates without claiming semantics."""

import platform
import hashlib
import re
from bisect import bisect_right
from pathlib import Path
from .model import digest, identity
from .._version import __version__


SCOPES = {
    "file",
    "package_body",
    "package_spec",
    "function",
    "procedure",
    "class",
    "block",
}


def build_index(input_path, *, encoding="utf-8", adapters=None):
    """Snapshot one file or a directory without executing source code.

    Args:
        input_path: Source file or directory; unsupported extensions are skipped.
        encoding: Strict decoding applied to every source file.
        adapters: Optional iterable of Adapter implementations replacing defaults.

    Returns:
        A JSON-serializable schema-1 index with exact source, tree and candidates.

    Raises:
        ValueError: No sources, invalid adapter contracts, or conflicting extensions.
        OSError: A source cannot be read.
        UnicodeError: A source cannot be decoded with the selected encoding.
    """
    from .adapters import builtin_adapters

    adapters = list(adapters if adapters is not None else builtin_adapters())
    lookup = {}
    for adapter in adapters:
        for extension in adapter.extensions:
            if extension.lower() in lookup:
                raise ValueError("duplicate adapter extension: " + extension)
            lookup[extension.lower()] = adapter
    source = Path(input_path).resolve()
    if not source.exists():
        raise ValueError("input does not exist")
    base = source if source.is_dir() else source.parent
    paths = sorted(source.rglob("*")) if source.is_dir() else [source]
    files = [
        p
        for p in paths
        if p.is_file()
        and not p.is_symlink()
        and p.suffix.lower() in lookup
        and not any(
            part.startswith(".")
            or part in {"node_modules", "__pycache__", "build", "dist"}
            for part in p.relative_to(base).parts
        )
    ]
    if not files:
        raise ValueError("no supported source files")
    sources, nodes, references, diagnostics = [], [], [], []
    used = {}
    for path in files:
        # Do not follow directory symlinks to files outside the input boundary.
        path.resolve().relative_to(base)
        rel = path.relative_to(base).as_posix()
        data = path.read_bytes()
        text = data.decode(encoding, errors="strict")
        adapter = lookup[path.suffix.lower()]
        parsed = adapter.parse(text, rel)
        line_starts = [0] + [i + 1 for i, c in enumerate(text) if c == "\n"]
        sid = identity("source", rel, digest(text))
        source_record = {
            "id": sid,
            "path": rel,
            "encoding": encoding,
            "original_sha256": hashlib.sha256(data).hexdigest(),
            "text_sha256": digest(text),
            "text": text,
            "adapter": adapter.name,
        }
        sources.append(source_record)
        used[adapter.name] = adapter.version

        def flatten(node, parent=None):
            nid = identity(sid, node.kind, node.start, node.end, node.name)
            record = {
                "id": nid,
                "source_id": sid,
                "parent_id": parent,
                "kind": node.kind,
                "name": node.name,
                "symbol": node.symbol,
                "start": node.start,
                "end": node.end,
                "header_end": node.header_end
                if node.header_end is not None
                else node.end,
                "start_line": bisect_right(line_starts, node.start),
                "end_line": bisect_right(line_starts, max(node.start, node.end - 1)),
                "confidence": node.confidence,
            }
            nodes.append(record)
            for child in sorted(node.children, key=lambda n: (n.start, n.end, n.kind)):
                flatten(child, nid)

        flatten(parsed.root)
        for reference in parsed.references:
            references.append(
                {
                    "source_id": sid,
                    "kind": reference.kind,
                    "symbol": reference.symbol,
                    "start": reference.start,
                    "end": reference.end,
                }
            )
        for diagnostic in parsed.diagnostics:
            diagnostics.append({"source_id": sid, **diagnostic})
    by_id = {n["id"]: n for n in nodes}
    source_by_id = {s["id"]: s for s in sources}
    child_nodes = {}
    roots = {}
    for n in nodes:
        if n["parent_id"] is None:
            roots[n["source_id"]] = n
        else:
            child_nodes.setdefault(n["parent_id"], []).append(n)
    child_starts = {}
    for parent, group in child_nodes.items():
        group.sort(key=lambda n: n["start"])
        child_starts[parent] = [n["start"] for n in group]
    scope_cache = {}

    def scopes(n):
        if n["id"] in scope_cache:
            return scope_cache[n["id"]]
        original_id = n["id"]
        result = []
        while n:
            if n["kind"] in SCOPES:
                result.append(n["id"])
            n = by_id.get(n["parent_id"])
        scope_cache[original_id] = result
        return result

    def qualified_name(n):
        parts = [n["symbol"]]
        p = by_id.get(n["parent_id"])
        while p:
            if (
                p["kind"]
                in {"package_body", "package_spec", "class", "function", "procedure"}
                and p["symbol"]
            ):
                parts.insert(0, p["symbol"])
            p = by_id.get(p["parent_id"])
        return ".".join(parts)

    qualified_symbols = {}
    scoped_symbols = {}
    package_scopes = {}
    for n in nodes:
        if n["kind"] in {"package_body", "package_spec"}:
            package_scopes.setdefault(n["symbol"], []).append(n["id"])
        if not n["symbol"]:
            continue
        adapter_name = source_by_id[n["source_id"]]["adapter"]
        qualified_symbols.setdefault((adapter_name, qualified_name(n)), []).append(n)
        if n["parent_id"]:
            scope = scopes(by_id[n["parent_id"]])[0]
            scoped_symbols.setdefault((scope, n["symbol"]), []).append(n)
    edges = []
    for ref in references:
        owner = roots[ref["source_id"]]
        if not owner["start"] <= ref["start"] < ref["end"] <= owner["end"]:
            raise ValueError("adapter reference outside source")
        while owner["id"] in child_nodes:
            pos = bisect_right(child_starts[owner["id"]], ref["start"]) - 1
            if pos < 0:
                break
            child = child_nodes[owner["id"]][pos]
            if not child["start"] <= ref["start"] < ref["end"] <= child["end"]:
                break
            owner = child
        # Definition headers are declarations, not evidence of executing a call.
        if (
            owner["symbol"]
            and ref["start"] < owner["header_end"]
            and ref["symbol"] == owner["symbol"]
        ):
            continue
        candidates = []
        # A dot inside a quoted Oracle identifier is not a qualification separator.
        qualified = "." in re.sub(r'"(?:[^"]|"")*"', "", ref["symbol"])
        if qualified:
            candidates = qualified_symbols.get(
                (source_by_id[ref["source_id"]]["adapter"], ref["symbol"]), []
            )
        else:
            for scope in scopes(owner):
                matches = scoped_symbols.get((scope, ref["symbol"]), [])
                scope_node = by_id[scope]
                if not matches and scope_node["kind"] in {
                    "package_body",
                    "package_spec",
                }:
                    for counterpart in package_scopes.get(scope_node["symbol"], []):
                        if counterpart != scope:
                            matches = matches + scoped_symbols.get(
                                (counterpart, ref["symbol"]), []
                            )
                if matches:
                    candidates = matches
                    break
        if ref["kind"] == "jump":
            candidates = [n for n in candidates if n["kind"] == "label"]
        elif ref["kind"] == "call":
            candidates = [
                n
                for n in candidates
                if n["kind"] in {"function", "procedure", "class", "declaration"}
            ]
        if ref["kind"] == "reference" and not candidates:
            continue
        ids = sorted({n["id"] for n in candidates})
        edge = {
            **ref,
            "owner_id": owner["id"],
            "target_ids": ids,
            "resolution": "candidate"
            if len(ids) == 1
            else "ambiguous"
            if ids
            else "unresolved",
            "evidence": "lexical; runtime binding and side effects are not proven",
        }
        edge["id"] = identity("edge", ref, ids)
        edges.append(edge)
    index = {
        "schema_version": 1,
        "generator": f"code2map/{__version__}",
        "runtime": {"python": platform.python_version()},
        "adapters": dict(sorted(used.items())),
        "sources": sources,
        "nodes": nodes,
        "edges": sorted(
            edges, key=lambda e: (e["source_id"], e["start"], e["kind"], e["symbol"])
        ),
        "diagnostics": diagnostics,
    }
    validate_index(index)
    return index


def validate_index(index):
    """Reject corrupt snapshots and broken adapter contracts before packaging."""
    if index.get("schema_version") != 1:
        raise ValueError("unsupported index schema")
    sources = {s["id"]: s for s in index["sources"]}
    nodes = {n["id"]: n for n in index["nodes"]}
    if len(sources) != len(index["sources"]) or len(nodes) != len(index["nodes"]):
        raise ValueError("duplicate source or node id")
    if not sources:
        raise ValueError("index has no sources")
    for s in sources.values():
        if (
            digest(s["text"]) != s["text_sha256"]
            or identity("source", s["path"], digest(s["text"])) != s["id"]
        ):
            raise ValueError("source snapshot hash mismatch")
    children = {}
    for n in nodes.values():
        s = sources[n["source_id"]]
        if not 0 <= n["start"] <= n["header_end"] <= n["end"] <= len(s["text"]):
            raise ValueError("invalid node span")
        if n["id"] != identity(
            n["source_id"], n["kind"], n["start"], n["end"], n["name"]
        ):
            raise ValueError("node id mismatch")
        parent = nodes.get(n["parent_id"])
        if n["parent_id"] is not None and parent is None:
            raise ValueError("missing parent")
        if parent:
            if (
                parent["source_id"] != n["source_id"]
                or not parent["start"] <= n["start"] <= n["end"] <= parent["end"]
            ):
                raise ValueError("child outside parent")
            # Also catches equal-span parent cycles without relying on recursion.
            seen = {n["id"]}
            p = parent
            while p:
                if p["id"] in seen:
                    raise ValueError("parent cycle")
                seen.add(p["id"])
                p = nodes.get(p["parent_id"])
            children.setdefault(parent["id"], []).append(n)
    for sibling_nodes in children.values():
        previous_end = -1
        for n in sorted(sibling_nodes, key=lambda x: (x["start"], x["end"])):
            if n["start"] < previous_end:
                raise ValueError("overlapping siblings")
            previous_end = n["end"]
    for s in sources.values():
        roots = [
            n
            for n in nodes.values()
            if n["source_id"] == s["id"] and n["parent_id"] is None
        ]
        if (
            len(roots) != 1
            or roots[0]["start"] != 0
            or roots[0]["end"] != len(s["text"])
        ):
            raise ValueError("source needs exactly one covering root")
    for e in index["edges"]:
        n = nodes[e["owner_id"]]
        if (
            e["source_id"] != n["source_id"]
            or not n["start"] <= e["start"] < e["end"] <= n["end"]
        ):
            raise ValueError("edge outside owner")
        if any(target not in nodes for target in e["target_ids"]):
            raise ValueError("missing edge target")
    for diagnostic in index["diagnostics"]:
        source = sources[diagnostic["source_id"]]
        if not 0 <= diagnostic["start"] <= diagnostic["end"] <= len(source["text"]):
            raise ValueError("diagnostic outside source")
    return {
        "status": "passed",
        "sources": len(sources),
        "nodes": len(nodes),
        "edges": len(index["edges"]),
    }
