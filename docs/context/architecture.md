# Architecture

[English](architecture.md) | [日本語](architecture_ja.md)

## Build a common map first

The partitioner works from a common index of the entire input: source snapshots, structural hierarchy and dependency candidates. Functions, blocks and cross-file relationships use the same node IDs.

There are four layers:

1. **Language adapters** read source and return a tree with positions and reference candidates.
2. **The common index** manages relative paths, source hashes, reproducible IDs, hierarchy and lexical candidate matching.
3. **Packing** partitions at structural boundaries and adds enclosing headers, dependency declarations and exception-region references.
4. **Validation** checks tree consistency, exact source excerpts, target coverage and budgets.

The engine has no dependency on an LLM, embeddings, a vector database or a particular inference API. Future compiler-backed adapters can supply the same tree and edge representation.

## Scope of determinism

The index excludes timestamps and absolute paths. Source IDs depend on the relative path and decoded-text hash. Node IDs depend on source ID, kind, range and name. Editing a source changes its IDs; tracking identities across edits is not guaranteed.

Python AST behavior depends on the interpreter, so its version is recorded. Java and C# record Tree-sitter and grammar versions. Fix source bytes, encoding, relative paths, runtime and adapter implementations, tokenizer vocabulary/options and packing settings to reproduce output byte for byte. Custom adapters and counters must themselves behave deterministically.

Hashes establish content consistency, not authorship or authenticity.

## Partitioning rules

1. If a whole node and mandatory context fit the input budget, keep that range as a candidate.
2. Otherwise recurse through its children, preserving the source gaps before, between and after them.
3. Do not cut a range with no children into arbitrary pieces. Return `oversized` if it exceeds the budget.
4. Greedily merge adjacent candidates from left to right, measuring the entire rebuilt payload each time.
5. Use remaining space for dependency declarations or signatures. Record the node ID and reason for every excerpt omitted by budget or count.

Gaps include comments, whitespace, opening/closing syntax and SQL*Plus separators. Concatenating packet targets in source order reconstructs each decoded source completely. Supporting context does not count toward target coverage.

A single large SQL statement, literal, header or unrecognized region can exceed the budget. Such a range is retained with an explicit status.

## Heading-first partitioning and raised cut points (next version, not yet implemented)

This section specifies the partitioning method `structural-heading-v1` to be added in the next version. **It is not implemented yet.** The default remains the rules above (`structural-greedy-v1`); this method is used only with `pack --algorithm structural-heading-v1`. See "Contracts added in the next version" in [Data contracts](contracts.md).

Partitioning by syntax alone can split or merge the procedural sections an author marked with comments for syntactic reasons only. Container headers (an `if` or `for` line, for example) and explanatory comments can also end up in a different packet from the code they describe. This method prefers the author's section breaks (headings) as boundaries and raises cut points to readable lines.

1. If a range fits the budget with its required context, it becomes a candidate (same as rule 1 above).
2. For a function or procedure range that does not fit, the first lines of the heading bands at the current level within that range become section boundaries. Sections are packed from the start and cut only where adding the next section would exceed the budget. Small sections share a packet with their neighbors.
3. Only a section that does not fit on its own descends to headings one level lower; when headings run out, it descends to syntax children (rule 2 above).
4. Every cut point, whether chosen by headings or by syntax, is raised in two steps.
   - (1) If only the header lines of a container (control, branch, block, handler) whose body starts at that position lie directly above, raise it to the first line of the container.
   - (2) If a run of line comments lies directly above that, raise it to the start of the run (skipping blank lines in between). Separators, change-history lines (the profile's `markers.change`), and heading band lines are not part of the run.
   This keeps container headers from being stranded at the end of the previous packet and keeps explanatory comments with the code they describe.
5. Boundaries chosen by headings are not removed by the final greedy merge.
6. Cuts are allowed only at line starts outside literals, block comments, declarations, statements, and syntax headers. Headings that cannot be cut stay as context and are annotated `HEADING_FALLBACK`.

Headings are detected from the profile, so for an index without a profile only the raising of cut points takes effect. Headings are the author's table of contents; their hierarchy is not treated as proof of control flow.

## Context and dependencies

When a target covers only part of an ancestor, its source header is attached. A split inside an ELSE branch retains the enclosing IF condition and ELSE position. Applicable structural exception-region references are retained; handler source is added when budget and dependency-count limits permit.

Lexical edges do not establish runtime reachability, overload selection, a variable's reaching definition or exception propagation. Even a single `candidate` is not a resolved semantic binding. Matching variable names is not proof of data flow.

Do not generalize a local finding such as “no updates” or “no exceptions” to the whole file. The payload states the target scope. Consumers must combine block results and re-examine source as needed for whole-program understanding.

## Extension boundaries

- Additional compiler-backed or Tree-sitter adapters
- Edges supported by external evidence such as PL/Scope
- Read/write, reaching definitions, control flow and transaction information
- Budgeted source retrieval and task-specific dependency priorities
- Incremental indexing and node correspondence across edits

These are future extensions. Version schema or adapter changes as appropriate before introducing incompatible behavior.
