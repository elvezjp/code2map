# Supported behavior and remaining work

[English](limitations.md) | [日本語](limitations_ja.md)

## What this version can establish

- Source preservation, structural partitioning and detection of target gaps/overlaps
- Reproducible output with a fixed environment, adapters, settings and counter
- Whether a payload fits or an indivisible oversized region remains
- Which original headers and dependency declarations were attached
- Which calls are unresolved/ambiguous and which supporting excerpts were omitted

## PL/SQL

The adapter is a lexical/procedural structure scanner, not the Oracle compiler. SQL statements are treated as units up to their terminator. Support for every Oracle version and grammar construct is not guaranteed.

SQL*Plus commands, conditional compilation, external Java procedures, specialized DDL/triggers and local functions inside SQL are outside the supported scope. When a failure is detected, the affected script unit is preserved as `opaque`. Accepted structures use `structural` confidence; acceptance does not prove Oracle validity or semantics.

Candidates come from names and lexical scopes. An identifier followed by parentheses can be a type or array access and still appear as a call candidate. Overloads, synonyms, database links, dynamic calls, privileges and runtime changes in package state are not resolved. PL/Scope import is not implemented.

## Python

The running interpreter's standard AST handles the syntax it supports. Imports are not loaded; dynamic attributes, decorator effects, monkey-patching and type inference are not analyzed. Variable references are lexical candidates, not complete assignment-order or `global`/`nonlocal` binding analysis.

## Java

Tree-sitter CST handles classes, methods, constructors, parameters, blocks, IF/ELSE, loops, switch statements and catch/finally. A file with syntax errors is preserved entirely as `opaque`.

The adapter does not resolve types, inheritance, dynamic dispatch or imported files. Qualified calls such as `this.method()` and generic constructor types can remain unresolved. Lambdas, switch expressions nested inside expressions and anonymous classes are not independently partitioned. Do-while is indivisible so its trailing condition is retained; a large one is `oversized`.

The index records Tree-sitter and Java grammar versions. Reproduction requires fixed Python, dependency versions, input and settings.

## C#

Structure comes from the `tree-sitter-c-sharp` grammar. Block-form namespaces are scopes; a file-scoped `namespace X;` is recorded as a leaf `import` node and does not qualify the names below it. Classes, structs, interfaces, records, enums, methods, constructors, properties, indexers, operators and local functions are nodes; property accessors are branches under the property. Control flow (if/else, loops, switch statement and expression, try/catch/finally, using, lock, checked, unsafe, fixed) splits along its bodies; `do` remains indivisible so the trailing condition is not separated. Lambdas, anonymous methods, query expressions and attributes are not split. `partial` types in different files are separate nodes and are not merged. Preprocessor lines (`#region`, `#if`, ...) are leaf `preproc` nodes; conditional compilation is not evaluated, so inactive branches are indexed as written. Calls, object creation, `goto` and identifiers are lexical candidates without overload, extension-method or type resolution. Syntax errors make the whole file opaque. The index records the Tree-sitter runtime and C# grammar versions.

## Context and semantic understanding

Supporting excerpts are mainly declarations and signatures. The engine does not generate summaries of callee updates or thrown exceptions. External dependencies remain unresolved when supporting source is unavailable.

Exception references are based on structural containment. Exact applicability, including inner handlers and rethrows, requires additional analysis.

Even `ready` packets may omit supporting excerpts. Consumers should inspect `omitted_context` and relations, then use `show` or the snapshot for additional source when needed. Consumers are responsible for budgeting any additional retrieval.

## Next priorities

1. Expand real PL/SQL compatibility corpora to reduce unrecognized regions and incorrect boundaries.
2. Accept PL/Scope/compiler evidence alongside, and distinctly from, lexical candidates.
3. Add read/write and control-flow relationships between blocks.
4. Evaluate downstream block explanations and whole-program synthesis to improve context selection.
5. Stabilize public APIs/schemas and expand evaluation corpora and usage examples.
