"""Conservative PL/SQL structural scanner, not an Oracle semantic compiler.

It recognizes balanced procedural constructs without interpreting SQL. A script
unit whose structure cannot be recognized is retained whole as an opaque node.
"""

from dataclasses import dataclass
import re
from ..model import Node, Parsed, Reference


@dataclass
class Token:
    value: str
    start: int
    end: int


class ParseError(ValueError):
    pass


TOKEN_PATTERN = re.compile(r"[A-Za-z_][A-Za-z_0-9$#]*|\d+(?:\.\d+)?|:=|=>|<<|>>|\S")


def tokenize(text: str) -> list[Token]:
    result = []
    i = 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        start = i
        if text.startswith("--", i):
            pos = text.find("\n", i)
            i = len(text) if pos < 0 else pos
            continue
        if text.startswith("/*", i):
            pos = text.find("*/", i + 2)
            if pos < 0:
                raise ParseError(f"unclosed comment at character {i}")
            i = pos + 2
            continue
        q = re.match(r"(?i)(?:n?q)'(.)", text[i : i + 4])
        if q:
            delimiter = q.group(1)
            closing = {"[": "]", "(": ")", "{": "}", "<": ">"}.get(delimiter, delimiter)
            pos = text.find(closing + "'", i + q.end())
            if pos < 0:
                raise ParseError(f"unclosed q literal at character {i}")
            i = pos + 2
            result.append(Token("#STRING", start, i))
            continue
        if text[i] in "'\"":
            quote = text[i]
            i += 1
            while i < len(text):
                if text[i] == quote:
                    i += 1
                    if i < len(text) and text[i] == quote:
                        i += 1
                        continue
                    break
                i += 1
            else:
                raise ParseError(f"unclosed literal at character {start}")
            result.append(Token(text[start:i] if quote == '"' else "#STRING", start, i))
            continue
        match = TOKEN_PATTERN.match(text, i)
        value = match.group()
        i += len(value)
        result.append(Token(value.upper(), start, i))
    return result


def is_identifier(value: str) -> bool:
    return bool(re.fullmatch(r'[A-Z_][A-Z_0-9$#]*|"(?:[^"]|"")+"', value))


class Scanner:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0

    def at(self, value):
        return self.i < len(self.tokens) and self.tokens[self.i].value == value

    def take(self, value=None):
        if self.i >= len(self.tokens) or (value and not self.at(value)):
            actual = self.tokens[self.i].value if self.i < len(self.tokens) else "EOF"
            raise ParseError(f"expected {value or 'token'}, found {actual}")
        token = self.tokens[self.i]
        self.i += 1
        return token

    def until(self, stops):
        depth = 0
        cases = 0
        start = self.i
        while self.i < len(self.tokens):
            v = self.tokens[self.i].value
            if depth == 0 and cases == 0 and v in stops:
                return self.tokens[start : self.i]
            if v == "(":
                depth += 1
            elif v == ")":
                depth -= 1
                if depth < 0:
                    raise ParseError("unbalanced parentheses")
            elif v == "CASE":
                cases += 1
            elif v == "END" and cases:
                cases -= 1
            self.i += 1
        raise ParseError("missing delimiter: " + ", ".join(sorted(stops)))

    def sequence(self, stops):
        nodes = []
        while self.i < len(self.tokens) and self.tokens[self.i].value not in stops:
            nodes.append(self.statement())
        return nodes

    def end(self, suffix=None):
        self.take("END")
        if suffix:
            self.take(suffix)
        if not self.at(";"):
            name = self.take().value
            if not is_identifier(name) or name in {"IF", "LOOP", "CASE", "END"}:
                raise ParseError("invalid END label")
        return self.take(";").end

    def handlers(self):
        start = self.take("EXCEPTION").start
        children = []
        while self.at("WHEN"):
            first = self.take()
            self.until({"THEN"})
            header = self.take("THEN").end
            body = self.sequence({"WHEN", "END"})
            finish = body[-1].end if body else header
            children.append(
                Node(
                    "handler",
                    first.start,
                    finish,
                    "WHEN",
                    header,
                    children=body,
                    confidence="structural",
                )
            )
        if not children:
            raise ParseError("EXCEPTION without WHEN")
        return Node(
            "exception",
            start,
            children[-1].end,
            "EXCEPTION",
            start + 9,
            children=children,
            confidence="structural",
        )

    def body(self, start, kind, name="", symbol="", declarations=None):
        header = self.take("BEGIN").end
        children = list(declarations or []) + self.sequence({"EXCEPTION", "END"})
        if self.at("EXCEPTION"):
            children.append(self.handlers())
        finish = self.end()
        # Header must not overlap declaration children.
        he = children[0].start if declarations else header
        return Node(kind, start, finish, name, he, symbol, "structural", children)

    def declaration(self):
        if self.at("FUNCTION") or self.at("PROCEDURE"):
            return self.subprogram()
        start = self.tokens[self.i].start
        tokens = self.until({";"})
        finish = self.take(";").end
        name = tokens[0].value if tokens else ""
        if name in {"TYPE", "SUBTYPE", "CURSOR"}:
            name = tokens[1].value if len(tokens) > 1 else ""
        if name in {"PRAGMA"}:
            name = ""
        return Node("declaration", start, finish, name, finish, name, "structural")

    def subprogram(self, start=None):
        first = self.take()
        name = self.take().value
        if not is_identifier(name):
            raise ParseError("invalid subprogram identifier")
        # Standalone schema-qualified names.
        if self.at("."):
            self.take()
            name += "." + self.take().value
        self.until({"IS", "AS", ";"})
        start = first.start if start is None else start
        if self.at(";"):
            end = self.take().end
            return Node("declaration", start, end, name, end, name, "structural")
        header = self.take().end
        decls = []
        while not self.at("BEGIN"):
            if self.i >= len(self.tokens):
                raise ParseError("subprogram body missing")
            decls.append(self.declaration())
        node = self.body(start, first.value.lower(), name, name, decls)
        node.header_end = header
        return node

    def package(self, start):
        self.take("PACKAGE")
        kind = "package_body" if self.at("BODY") else "package_spec"
        if self.at("BODY"):
            self.take()
        name = self.take().value
        if self.at("."):
            self.take()
            name += "." + self.take().value
        self.until({"IS", "AS"})
        header = self.take().end
        children = []
        while not self.at("BEGIN") and not self.at("END"):
            if self.i >= len(self.tokens):
                raise ParseError("package END missing")
            children.append(self.declaration())
        if self.at("BEGIN"):
            initialization = self.body(
                self.tokens[self.i].start, "initialization", "initialization"
            )
            children.append(initialization)
            finish = initialization.end
        else:
            finish = self.end()
        return Node(kind, start, finish, name, header, name, "structural", children)

    def statement(self):
        first = self.tokens[self.i]
        v = first.value
        if v == "CREATE":
            self.take()
            if self.at("OR"):
                self.take()
                self.take("REPLACE")
            if self.at("EDITIONABLE") or self.at("NONEDITIONABLE"):
                self.take()
            if self.at("PACKAGE"):
                return self.package(first.start)
            if self.at("FUNCTION") or self.at("PROCEDURE"):
                return self.subprogram(first.start)
            self.until({";"})
            end = self.take().end
            return Node(
                "statement", first.start, end, "CREATE", end, confidence="structural"
            )
        if v in {"FUNCTION", "PROCEDURE"}:
            return self.subprogram()
        if v == "BEGIN":
            return self.body(first.start, "block", "BEGIN")
        if v == "DECLARE":
            self.take()
            declarations = []
            while not self.at("BEGIN"):
                declarations.append(self.declaration())
            node = self.body(first.start, "block", "DECLARE", declarations=declarations)
            node.header_end = first.end
            return node
        if v == "IF":
            self.take()
            self.until({"THEN"})
            header = self.take().end
            body = self.sequence({"ELSIF", "ELSE", "END"})
            branches = []
            while self.at("ELSIF") or self.at("ELSE"):
                branch = self.take()
                if branch.value == "ELSIF":
                    self.until({"THEN"})
                    bh = self.take().end
                else:
                    bh = branch.end
                bc = self.sequence({"ELSIF", "ELSE", "END"})
                branches.append(
                    Node(
                        "branch",
                        branch.start,
                        bc[-1].end if bc else bh,
                        branch.value,
                        bh,
                        confidence="structural",
                        children=bc,
                    )
                )
            return Node(
                "control",
                first.start,
                self.end("IF"),
                "IF",
                header,
                confidence="structural",
                children=body + branches,
            )
        if v in {"LOOP", "FOR", "WHILE"}:
            if v != "LOOP":
                self.until({"LOOP"})
            header = self.take("LOOP").end
            children = self.sequence({"END"})
            return Node(
                "control",
                first.start,
                self.end("LOOP"),
                v,
                header,
                confidence="structural",
                children=children,
            )
        if v == "CASE":
            self.take()
            self.until({"WHEN"})
            header = self.tokens[self.i].start
            children = []
            while self.at("WHEN") or self.at("ELSE"):
                branch = self.take()
                if branch.value == "WHEN":
                    self.until({"THEN"})
                    bh = self.take().end
                else:
                    bh = branch.end
                bc = self.sequence({"WHEN", "ELSE", "END"})
                children.append(
                    Node(
                        "branch",
                        branch.start,
                        bc[-1].end if bc else bh,
                        branch.value,
                        bh,
                        confidence="structural",
                        children=bc,
                    )
                )
            return Node(
                "control",
                first.start,
                self.end("CASE"),
                "CASE",
                header,
                confidence="structural",
                children=children,
            )
        if v == "<<":
            self.take()
            label = self.take().value
            he = self.take(">>").end
            child = self.statement()
            return Node(
                "label", first.start, child.end, label, he, label, "structural", [child]
            )
        if v in {"END", "EXCEPTION", "ELSE", "ELSIF", "WHEN"}:
            raise ParseError("unexpected " + v)
        self.until({";"})
        end = self.take().end
        return Node("statement", first.start, end, v, end, confidence="structural")


class PLSQLAdapter:
    name = "plsql-structural"
    version = "1"
    extensions = (".sql", ".pks", ".pkb", ".pls", ".plsql")

    def parse(self, text: str, path: str) -> Parsed:
        result = Parsed(Node("file", 0, len(text), path, 0))
        try:
            tokens = tokenize(text)
        except ParseError as exc:
            result.root.children = [Node("opaque", 0, len(text), confidence="unknown")]
            result.diagnostics.append(
                {
                    "code": "PLSQL_LEX_ERROR",
                    "message": str(exc),
                    "start": 0,
                    "end": len(text),
                }
            )
            return result
        # SQL*Plus separators count only outside strings and comments.
        groups = [[]]
        for token in tokens:
            ls = text.rfind("\n", 0, token.start) + 1
            le = text.find("\n", token.end)
            if (
                token.value == "/"
                and text[ls : le if le >= 0 else len(text)].strip() == "/"
            ):
                groups.append([])
            else:
                groups[-1].append(token)
        for group in groups:
            if not group:
                continue
            try:
                nodes = Scanner(group).sequence(set())
                result.root.children.extend(nodes)
            except (ParseError, IndexError, RecursionError) as exc:
                result.root.children.append(
                    Node("opaque", group[0].start, group[-1].end, confidence="unknown")
                )
                result.diagnostics.append(
                    {
                        "code": "PLSQL_STRUCTURE_UNKNOWN",
                        "message": str(exc),
                        "start": group[0].start,
                        "end": group[-1].end,
                    }
                )
                continue
            reserved = {
                "IF",
                "ELSIF",
                "WHILE",
                "FOR",
                "CASE",
                "WHEN",
                "IN",
                "VALUES",
                "RETURN",
                "SELECT",
                "INSERT",
                "UPDATE",
                "DELETE",
                "MERGE",
                "INTO",
                "AS",
                "IS",
                "TYPE",
                "TABLE",
                "RECORD",
                "EXISTS",
                "NOT",
                "AND",
                "OR",
                "NULL",
                "COMMIT",
                "ROLLBACK",
            }
            i = 0
            while i < len(group):
                token = group[i]
                if not is_identifier(token.value) or token.value in reserved:
                    i += 1
                    continue
                symbol = token.value
                j = i + 1
                while (
                    j + 1 < len(group)
                    and group[j].value == "."
                    and is_identifier(group[j + 1].value)
                ):
                    symbol += "." + group[j + 1].value
                    j += 2
                previous = group[i - 1].value if i else ""
                following = group[j].value if j < len(group) else ""
                if previous == "GOTO":
                    kind = "jump"
                elif following == "(" and previous not in {
                    "FUNCTION",
                    "PROCEDURE",
                    "CURSOR",
                    "TYPE",
                }:
                    kind = "call"
                elif following == ";" and previous in {"BEGIN", ";", "THEN", "ELSE"}:
                    kind = "call"
                else:
                    kind = "reference"
                result.references.append(
                    Reference(kind, symbol, token.start, group[j - 1].end)
                )
                i = j
        return result
