"""Java CST adapter with exact source spans and lexical dependency candidates."""

from importlib.metadata import version

from tree_sitter import Language, Parser
import tree_sitter_java

from ..model import Node, Parsed, Reference


CLASSES = {
    "class_declaration",
    "interface_declaration",
    "enum_declaration",
    "record_declaration",
    "annotation_type_declaration",
}
FUNCTIONS = {
    "method_declaration",
    "constructor_declaration",
    "compact_constructor_declaration",
}
CONTROLS = {
    "if_statement",
    "for_statement",
    "enhanced_for_statement",
    "while_statement",
    "do_statement",
    "try_statement",
    "try_with_resources_statement",
    "synchronized_statement",
    "switch_expression",
    "labeled_statement",
}
BRANCHES = {"switch_block_statement_group", "switch_rule"}
CONTAINERS = {
    "class_body",
    "interface_body",
    "enum_body",
    "enum_body_declarations",
    "switch_block",
}
PARAMETERS = {"formal_parameter", "spread_parameter", "receiver_parameter"}


class JavaAdapter:
    """Read Java structure without compiling, resolving types, or executing code.

    A malformed file is retained as one opaque region. Nested expressions remain
    indivisible; calls and identifiers are lexical evidence, not Java bindings.
    """

    name = "java-tree-sitter"
    extensions = (".java",)

    @property
    def version(self) -> str:
        """Record grammar and runtime versions used to choose source boundaries."""
        return (
            f"1;tree-sitter={version('tree-sitter')};java={version('tree-sitter-java')}"
        )

    def parse(self, text: str, path: str) -> Parsed:
        """Return a non-overlapping tree whose offsets index Unicode characters."""
        raw = text.encode("utf-8")
        tree = Parser(Language(tree_sitter_java.language())).parse(raw)
        root = Node("file", 0, len(text), path, 0)
        parsed = Parsed(root)
        if tree.root_node.has_error:
            root.children = [Node("opaque", 0, len(text), confidence="unknown")]
            parsed.diagnostics.append(
                {
                    "code": "JAVA_PARSE_ERROR",
                    "message": "Java CST contains syntax errors; file retained intact",
                    "start": 0,
                    "end": len(text),
                }
            )
            return parsed

        # Tree-sitter offsets are UTF-8 bytes, whereas the common contract uses
        # Unicode characters. Build once, avoiding repeated prefix decoding.
        positions = {0: 0}
        offset = 0
        for i, char in enumerate(text):
            offset += len(char.encode("utf-8"))
            positions[offset] = i + 1

        def source(item):
            return raw[item.start_byte : item.end_byte].decode("utf-8") if item else ""

        def convert(item):
            kind = item.type
            if kind in {"line_comment", "block_comment"}:
                return None  # Comments remain in exact source gaps.
            start, end = positions[item.start_byte], positions[item.end_byte]
            name = source(item.child_by_field_name("name"))
            body = item.child_by_field_name("body")
            children = []
            header_end = end
            symbol = ""
            if kind in CLASSES:
                category, symbol = "class", name
            elif kind in FUNCTIONS:
                category, symbol = "function", name
            elif kind in PARAMETERS:
                category, symbol = "parameter", name
            elif kind in {"field_declaration", "local_variable_declaration"}:
                category = "declaration"
                declarations = [
                    c for c in item.named_children if c.type == "variable_declarator"
                ]
                if len(declarations) == 1:
                    symbol = source(declarations[0].child_by_field_name("name"))
                    name = symbol
            elif kind in {"catch_clause", "finally_clause"}:
                category = "handler"
                body = body or next(
                    (c for c in item.named_children if c.type == "block"), None
                )
            elif kind == "block":
                category, header_end = "block", start + 1
            elif kind in CONTROLS:
                category = "control"
            elif kind in BRANCHES:
                category = "branch"
            elif kind in {"import_declaration", "package_declaration"}:
                category = "import"
            else:
                category = "statement"

            if body:
                header_end = positions[body.start_byte] + (
                    1 if source(body).startswith("{") else 0
                )
            if kind in CLASSES and body:
                children.extend(convert_many(body.named_children))
            elif kind in FUNCTIONS:
                params = item.child_by_field_name("parameters")
                if params:
                    children.extend(
                        convert_many(
                            c for c in params.named_children if c.type in PARAMETERS
                        )
                    )
                if body:
                    children.extend(convert_many([body]))
            elif kind == "if_statement":
                consequence = item.child_by_field_name("consequence")
                alternative = item.child_by_field_name("alternative")
                header_end = positions[consequence.start_byte]
                children.extend(convert_many([consequence]))
                if alternative:
                    # Include the actual source gap with `else`, keeping branch
                    # polarity available after descending into a large body.
                    alt = convert(alternative)
                    children.append(
                        Node(
                            "branch",
                            positions[consequence.end_byte],
                            positions[alternative.end_byte],
                            "else",
                            positions[alternative.start_byte],
                            children=[alt],
                        )
                    )
            elif (
                category in {"control", "handler", "branch", "block"}
                and kind != "do_statement"
            ):
                for child in item.named_children:
                    if (
                        child.type
                        in CONTROLS
                        | BRANCHES
                        | {"block", "catch_clause", "finally_clause"}
                        or child.type.endswith("_statement")
                        or child.type in CONTAINERS
                        or child.type
                        in {"local_variable_declaration", "class_declaration"}
                    ):
                        if child.type in CONTAINERS:
                            children.extend(convert_many(child.named_children))
                        else:
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
            if item.type == "method_invocation":
                name = item.child_by_field_name("name")
                receiver = item.child_by_field_name("object")
                if name:
                    symbol = source(name)
                    first = name
                    if receiver:
                        symbol = source(receiver) + "." + symbol
                        first = receiver
                    parsed.references.append(
                        Reference(
                            "call",
                            symbol,
                            positions[first.start_byte],
                            positions[name.end_byte],
                        )
                    )
            elif item.type == "object_creation_expression":
                target = item.child_by_field_name("type")
                if target:
                    parsed.references.append(
                        Reference(
                            "call",
                            source(target),
                            positions[target.start_byte],
                            positions[target.end_byte],
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
