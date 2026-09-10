"""C# CST adapter with exact source spans and lexical dependency candidates.

Mirrors the Java adapter: Tree-sitter gives a concrete syntax tree, the adapter
turns declarations and control flow into a non-overlapping interval tree, and
calls/identifiers are recorded as lexical evidence only. No compilation, no
symbol binding, no execution.
"""

from importlib.metadata import version

import tree_sitter_c_sharp
from tree_sitter import Language, Parser

from ..model import Node, Parsed, Reference

CLASSES = {
    "class_declaration",
    "struct_declaration",
    "interface_declaration",
    "record_declaration",
    "record_struct_declaration",
    "enum_declaration",
}
FUNCTIONS = {
    "method_declaration",
    "constructor_declaration",
    "destructor_declaration",
    "operator_declaration",
    "conversion_operator_declaration",
    "local_function_statement",
    "property_declaration",
    "indexer_declaration",
}
DECLARATIONS = {
    "field_declaration",
    "event_field_declaration",
    "event_declaration",
    "delegate_declaration",
    "enum_member_declaration",
    "local_declaration_statement",
}
CONTROLS = {
    "if_statement",
    "for_statement",
    "foreach_statement",
    "while_statement",
    "do_statement",
    "try_statement",
    "switch_statement",
    "switch_expression",
    "using_statement",
    "lock_statement",
    "checked_statement",
    "unsafe_statement",
    "fixed_statement",
}
BRANCHES = {"switch_section", "switch_expression_arm", "accessor_declaration"}
HANDLERS = {"catch_clause", "finally_clause"}
CONTAINERS = {
    "declaration_list",
    "enum_member_declaration_list",
    "switch_body",
    "accessor_list",
    "global_statement",
}
IMPORTS = {"using_directive", "extern_alias_directive", "global_attribute"}
PARAMETERS = {"parameter"}
# Conditional-compilation blocks carry the declarations they guard until the
# matching #endif. They are indexed as written; no condition is evaluated.
PREPROC_BLOCKS = {"preproc_if", "preproc_elif", "preproc_else"}


class CSharpAdapter:
    """Read C# structure without compiling, resolving types, or executing code.

    A malformed file is retained as one opaque region. Expressions (lambdas,
    anonymous methods, queries) remain indivisible; calls and identifiers are
    lexical evidence, not .NET bindings. Preprocessor directives such as
    ``#region`` are kept as leaf ``preproc`` nodes so their positions survive,
    but they never become structural regions.
    """

    name = "csharp-tree-sitter"
    extensions = (".cs",)

    @property
    def version(self) -> str:
        """Record grammar and runtime versions used to choose source boundaries."""
        return (
            f"1;tree-sitter={version('tree-sitter')};"
            f"c-sharp={version('tree-sitter-c-sharp')}"
        )

    def parse(self, text: str, path: str) -> Parsed:
        """Return a non-overlapping tree whose offsets index Unicode characters."""
        raw = text.encode("utf-8")
        tree = Parser(Language(tree_sitter_c_sharp.language())).parse(raw)
        root = Node("file", 0, len(text), path, 0)
        parsed = Parsed(root)
        if tree.root_node.has_error:
            root.children = [Node("opaque", 0, len(text), confidence="unknown")]
            parsed.diagnostics.append(
                {
                    "code": "CSHARP_PARSE_ERROR",
                    "message": "C# CST contains syntax errors; file retained intact",
                    "start": 0,
                    "end": len(text),
                }
            )
            return parsed

        # Tree-sitter offsets are UTF-8 bytes; the common contract counts
        # Unicode characters. A leading BOM is one character like any other.
        positions = {0: 0}
        offset = 0
        for i, char in enumerate(text):
            offset += len(char.encode("utf-8"))
            positions[offset] = i + 1

        def source(item):
            return raw[item.start_byte : item.end_byte].decode("utf-8") if item else ""

        def plain_name(item):
            """Identifier text without generic type arguments."""
            if item is None:
                return ""
            if item.type == "generic_name":
                head = next(
                    (c for c in item.named_children if c.type == "identifier"), None
                )
                return source(head)
            return source(item)

        def statement_like(child):
            return (
                child.type in CONTROLS | BRANCHES | HANDLERS | CONTAINERS
                or child.type in {"block", "labeled_statement", "goto_statement"}
                or child.type.endswith("_statement")
                or child.type in DECLARATIONS
                or child.type in CLASSES
                or child.type in PREPROC_BLOCKS
                or child.type == "local_function_statement"
            )

        def structural(child):
            """Anything that may sit inside a type body or a #if block."""
            return (
                statement_like(child)
                or child.type in FUNCTIONS
                or child.type in IMPORTS
                or child.type
                in {"namespace_declaration", "file_scoped_namespace_declaration"}
                or child.type.startswith("preproc_")
            )

        def first_line_end(item):
            head = source(item).split("\n", 1)[0]
            return positions[item.start_byte + len(head.encode("utf-8"))]

        def convert_switch_sections(sections):
            """Merge label-only sections into the section that carries the body.

            `case 1:` followed by `case 2:` shares one body; Tree-sitter returns
            the first label as an empty section. Keeping both labels in one
            branch header preserves that the body also runs for `case 1:`.
            """
            result = []
            pending_start = None
            for section in sections:
                has_body = any(statement_like(c) for c in section.named_children)
                if not has_body:
                    if pending_start is None:
                        pending_start = positions[section.start_byte]
                    continue
                node = convert(section)
                if node is not None and pending_start is not None:
                    node.start = pending_start
                    node.name = "switch_section"
                pending_start = None
                if node is not None:
                    result.append(node)
            if pending_start is not None and result:
                # Trailing label-only sections have no body of their own; the
                # gap keeps their text and the coverage stays exact.
                pass
            return result

        def convert(item):
            kind = item.type
            if kind == "comment":
                return None  # Comments remain in exact source gaps.
            start, end = positions[item.start_byte], positions[item.end_byte]
            name = plain_name(item.child_by_field_name("name"))
            body = item.child_by_field_name("body")
            children = []
            header_end = end
            symbol = ""
            if kind == "namespace_declaration":
                category, symbol = "namespace", name
            elif kind == "file_scoped_namespace_declaration":
                # No body: the rest of the file belongs to it. Keep as a leaf.
                category, name = "import", "namespace " + name
            elif kind in CLASSES:
                category, symbol = "class", name
            elif kind in FUNCTIONS:
                category = "function"
                symbol = name or ("this[]" if kind == "indexer_declaration" else "")
                if kind == "operator_declaration":
                    symbol = "operator " + source(item.child_by_field_name("operator"))
                elif kind == "conversion_operator_declaration":
                    symbol = "operator " + source(item.child_by_field_name("type"))
                elif kind == "destructor_declaration":
                    symbol = "~" + name
                name = symbol or name
            elif kind in PARAMETERS:
                category, symbol = "parameter", name
            elif kind in DECLARATIONS:
                category = "declaration"
                if kind in {
                    "enum_member_declaration",
                    "delegate_declaration",
                    "event_declaration",
                }:
                    symbol = name
                else:
                    declarators = [
                        d
                        for v in item.named_children
                        if v.type == "variable_declaration"
                        for d in v.named_children
                        if d.type == "variable_declarator"
                    ]
                    if len(declarators) == 1:
                        symbol = source(declarators[0].child_by_field_name("name"))
                name = symbol or name
            elif kind in HANDLERS:
                category = "handler"
                body = body or next(
                    (c for c in item.named_children if c.type == "block"), None
                )
            elif kind == "block":
                category, header_end = "block", start + 1
            elif kind == "labeled_statement":
                category = "label"
                label = next(
                    (c for c in item.named_children if c.type == "identifier"), None
                )
                symbol = name = source(label)
            elif kind in CONTROLS:
                category = "control"
            elif kind in BRANCHES:
                category = "branch"
                if kind == "accessor_declaration":
                    name = source(item.child_by_field_name("name")) or kind
            elif kind in IMPORTS:
                category = "import"
            elif kind in PREPROC_BLOCKS:
                category = "preproc"
                name = source(item).splitlines()[0].strip() if source(item) else kind
                header_end = first_line_end(item)
                children.extend(
                    convert_many(c for c in item.named_children if structural(c))
                )
                if children:
                    header_end = min(header_end, children[0].start)
            elif kind.startswith("preproc_"):
                category = "preproc"
                name = source(item).splitlines()[0].strip() if source(item) else kind
            else:
                category = "statement"

            if body is not None:
                header_end = positions[body.start_byte] + (
                    1 if source(body).startswith("{") else 0
                )
            if kind in PREPROC_BLOCKS:
                pass  # children were collected above
            elif kind in {"namespace_declaration"} | CLASSES:
                params = item.child_by_field_name("parameters")
                if params is not None:  # positional records
                    children.extend(
                        convert_many(
                            c for c in params.named_children if c.type in PARAMETERS
                        )
                    )
                if body is not None:
                    children.extend(convert_many(body.named_children))
            elif kind in FUNCTIONS:
                params = item.child_by_field_name("parameters")
                if params is not None:
                    children.extend(
                        convert_many(
                            c for c in params.named_children if c.type in PARAMETERS
                        )
                    )
                accessors = item.child_by_field_name("accessors")
                if accessors is not None:
                    header_end = positions[accessors.start_byte] + 1
                    children.extend(convert_many(accessors.named_children))
                elif body is not None and body.type == "block":
                    children.extend(convert_many([body]))
                elif body is not None:
                    # Expression-bodied member: the arrow clause is the body. A
                    # switch expression inside it still splits along its arms.
                    header_end = positions[body.start_byte]
                    children.extend(
                        convert_many(
                            c for c in body.named_children if c.type == "switch_expression"
                        )
                    )
            elif kind == "if_statement":
                consequence = item.child_by_field_name("consequence")
                alternative = item.child_by_field_name("alternative")
                header_end = positions[consequence.start_byte]
                children.extend(convert_many([consequence]))
                if alternative is not None:
                    alt = convert(alternative)
                    children.append(
                        Node(
                            "branch",
                            positions[consequence.end_byte],
                            positions[alternative.end_byte],
                            "else",
                            positions[alternative.start_byte],
                            children=[alt] if alt is not None else [],
                        )
                    )
            elif kind == "labeled_statement":
                for child in item.named_children:
                    if statement_like(child):
                        children.extend(convert_many([child]))
                if children:
                    header_end = children[0].start
            elif kind == "switch_statement":
                sections = [
                    c for c in (body.named_children if body is not None else [])
                    if c.type == "switch_section"
                ]
                children.extend(convert_switch_sections(sections))
            elif (
                category in {"control", "handler", "branch", "block"}
                and kind not in {"do_statement", "switch_expression_arm"}
            ):
                for child in item.named_children:
                    if statement_like(child):
                        children.extend(convert_many([child]))
                if children and kind != "block" and body is None:
                    header_end = min(header_end, children[0].start)
            return Node(
                category,
                start,
                end,
                name or kind,
                header_end,
                symbol,
                children=children,
            )

        def convert_many(items):
            result = []
            for item in items:
                if item.type in CONTAINERS:
                    result.extend(convert_many(item.named_children))
                else:
                    converted = convert(item)
                    if converted is not None:
                        result.append(converted)
            return result

        root.children = convert_many(tree.root_node.named_children)

        pending = [tree.root_node]
        while pending:
            item = pending.pop()
            if item.type == "invocation_expression":
                function = item.child_by_field_name("function")
                if function is not None:
                    if function.type == "member_access_expression":
                        receiver = function.child_by_field_name("expression")
                        member = function.child_by_field_name("name")
                        symbol = source(receiver) + "." + plain_name(member)
                        first, last = receiver, member
                    else:
                        symbol = plain_name(function)
                        first = last = function
                    if symbol.strip("."):
                        parsed.references.append(
                            Reference(
                                "call",
                                symbol,
                                positions[first.start_byte],
                                positions[last.end_byte],
                            )
                        )
            elif item.type == "object_creation_expression":
                target = item.child_by_field_name("type")
                if target is not None:
                    parsed.references.append(
                        Reference(
                            "call",
                            plain_name(target),
                            positions[target.start_byte],
                            positions[target.end_byte],
                        )
                    )
            elif item.type == "goto_statement":
                label = next(
                    (c for c in item.named_children if c.type == "identifier"), None
                )
                if label is not None:
                    parsed.references.append(
                        Reference(
                            "jump",
                            source(label),
                            positions[label.start_byte],
                            positions[label.end_byte],
                        )
                    )
            elif item.type == "identifier":
                parsed.references.append(
                    Reference(
                        "reference",
                        source(item),
                        positions[item.start_byte],
                        positions[item.end_byte],
                    )
                )
            pending.extend(reversed(item.named_children))
        return parsed
