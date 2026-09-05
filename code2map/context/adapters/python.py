"""Python AST adapter; no imports or source execution are performed."""

import ast
from ..model import Node, Parsed, Reference


class PythonAdapter:
    name = "python-ast"
    # Runtime minor is also recorded in the index: AST behavior can change.
    version = "1"
    extensions = (".py",)

    def parse(self, text: str, path: str) -> Parsed:
        root = Node("file", 0, len(text), path, 0)
        parsed = Parsed(root)
        try:
            tree = ast.parse(text, filename=path)
        except (SyntaxError, ValueError, RecursionError) as exc:
            root.children = [Node("opaque", 0, len(text), confidence="unknown")]
            parsed.diagnostics.append(
                {
                    "code": "PYTHON_PARSE_ERROR",
                    "message": str(exc),
                    "start": 0,
                    "end": len(text),
                }
            )
            return parsed
        lines = text.splitlines(keepends=True)
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line))

        def position(line, byte_col):
            return offsets[line - 1] + len(
                lines[line - 1].encode("utf-8")[:byte_col].decode("utf-8")
            )

        def span(item):
            return position(item.lineno, item.col_offset), position(
                item.end_lineno, item.end_col_offset
            )

        def qualified(item):
            if isinstance(item, ast.Name):
                return item.id
            if isinstance(item, ast.Attribute):
                base = qualified(item.value)
                return base + "." + item.attr if base else ""
            return ""

        def convert(item):
            start, end = span(item)
            symbol = ""
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                kind = "class" if isinstance(item, ast.ClassDef) else "function"
                symbol = item.name
                if item.decorator_list:
                    start = min(start, *(span(d)[0] - 1 for d in item.decorator_list))
            elif isinstance(item, (ast.Import, ast.ImportFrom)):
                kind = "import"
            elif isinstance(item, (ast.Assign, ast.AnnAssign)):
                kind = "declaration"
                targets = (
                    item.targets if isinstance(item, ast.Assign) else [item.target]
                )
                if len(targets) == 1 and isinstance(targets[0], ast.Name):
                    symbol = targets[0].id
            elif isinstance(
                item,
                (
                    ast.If,
                    ast.For,
                    ast.AsyncFor,
                    ast.While,
                    ast.Try,
                    ast.With,
                    ast.AsyncWith,
                    ast.Match,
                ),
            ):
                kind = "control"
            else:
                kind = "statement"
            children = [
                convert(child)
                for child in getattr(item, "body", [])
                if isinstance(child, ast.stmt)
            ]
            signature_end = children[0].start if children else end
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                arguments = (
                    item.args.posonlyargs + item.args.args + item.args.kwonlyargs
                )
                arguments += [a for a in (item.args.vararg, item.args.kwarg) if a]
                for arg in arguments:
                    astart, aend = span(arg)
                    children.append(
                        Node("parameter", astart, aend, arg.arg, aend, arg.arg)
                    )
            for handler in getattr(item, "handlers", []):
                hs, he = span(handler)
                hc = [convert(c) for c in handler.body]
                children.append(
                    Node(
                        "handler",
                        hs,
                        he,
                        "except",
                        hc[0].start if hc else he,
                        children=hc,
                    )
                )
            for field, label in (("orelse", "else"), ("finalbody", "finally")):
                branch_body = [
                    convert(child)
                    for child in getattr(item, field, [])
                    if isinstance(child, ast.stmt)
                ]
                if branch_body:
                    previous_end = max(
                        (c.end for c in children if c.end <= branch_body[0].start),
                        default=start,
                    )
                    # Preserve the actual source gap containing else/finally. An elif
                    # is represented by a nested If whose header carries its guard.
                    bs = (
                        previous_end
                        if text[previous_end : branch_body[0].start].strip()
                        else branch_body[0].start
                    )
                    children.append(
                        Node(
                            "branch",
                            bs,
                            branch_body[-1].end,
                            label,
                            branch_body[0].start,
                            children=branch_body,
                        )
                    )
            for case in getattr(item, "cases", []):
                # ast.match_case has no own positions; pattern and body provide them.
                cs = max(start, span(case.pattern)[0] - len("case "))
                cc = [convert(c) for c in case.body]
                children.append(
                    Node("branch", cs, cc[-1].end, "case", cc[0].start, children=cc)
                )
            children.sort(key=lambda n: n.start)
            header_end = signature_end
            return Node(
                kind,
                start,
                end,
                symbol or type(item).__name__,
                header_end,
                symbol,
                children=children,
            )

        root.children = [convert(item) for item in tree.body]
        for item in ast.walk(tree):
            if isinstance(item, ast.Call):
                name = qualified(item.func)
                if name:
                    s, e = span(item.func)
                    parsed.references.append(Reference("call", name, s, e))
            elif isinstance(item, ast.Name) and isinstance(item.ctx, ast.Load):
                s, e = span(item)
                parsed.references.append(Reference("reference", item.id, s, e))
        return parsed
