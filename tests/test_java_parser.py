from code2map.parsers.java_parser import JavaParser


def test_java_parser_extracts_symbols():
    parser = JavaParser()
    symbols, warnings = parser.parse("tests/fixtures/sample.java")
    assert warnings == []
    names = {(s.kind, s.display_name()) for s in symbols}
    assert ("class", "Sample") in names
    assert ("method", "Sample#work") in names


def test_java8_syntax_parses_successfully():
    # tree-sitter は Java 8+構文を正常にパースできる
    parser = JavaParser()
    symbols, warnings = parser.parse("tests/fixtures/java8_syntax.java")
    assert warnings == []
    names = {(s.kind, s.display_name()) for s in symbols}
    assert ("class", "Java8Syntax") in names
    assert ("class", "Java8Syntax_Status") in names
    assert ("method", "Java8Syntax_Status#getKeys") in names


def test_java8_syntax_constructor_extracted():
    parser = JavaParser()
    symbols, _ = parser.parse("tests/fixtures/java8_syntax.java")
    names = {(s.kind, s.display_name()) for s in symbols}
    assert ("method", "Java8Syntax_Status#<init>") in names
