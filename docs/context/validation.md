# Validation record for the 0.4.0 development branch

[English](validation.md) | [日本語](validation_ja.md)

Local checks performed on macOS on 2026-09-05:

| Check | Result |
| --- | --- |
| Full suite, Python 3.11.14 | 66 passed |
| Full suite, Python 3.13.11 | 66 passed |
| Full suite, Python 3.14.2 | 66 passed |
| Ruff on maintained sources | Passed |
| Legacy output comparison against `d90beee330bca581d0a52eddec38362c3b28d50a` | Byte-identical outputs for 7 fixtures |
| Source distribution and wheel build | Passed |
| Wheel installed in a fresh Python 3.12.12 environment | Version, mixed-language index, pack, check and legacy Java build passed |

The seven legacy fixtures were `sample.py`, `sample.java`, `java8_syntax.java`, `large_file.py`, `function_only.py`, `empty.py`, and `comments_only.py`. The comparison used the same input paths for both versions and compared every generated file's bytes, including `INDEX.md`, `MAP.json`, and `parts/`.

The complete suite contains 30 existing tests plus 36 context-engine tests. New coverage includes exact whole-source reconstruction, Unicode and CRLF, multiple source languages, enclosing branch conditions and exception references, unresolved and ambiguous lexical calls, custom adapters and counters, oversized/opaque regions, context omission integrity, and CLI exit behavior.

The lockfile retains the existing dependency versions (Tree-sitter 0.25.2 and Java grammar 0.23.5). The fresh wheel installation additionally exercised Tree-sitter 0.26.0 with Java grammar 0.23.5. This is not an exhaustive dependency-version compatibility claim.

CI is configured for Linux, Windows and macOS with Python 3.11, 3.13 and 3.14; those hosted runs are separate from this local record. These tests establish structural and output contracts on fixtures, not complete Oracle/Java/Python semantic analysis or improved downstream LLM accuracy on production systems.

## Documentation verification

The documentation follow-up on 2026-09-05 checked 20 current root/context Markdown pages and 111 local links/heading references. Seven document pairs (root README, build specification and five context documents) have matching executable examples and language-switch navigation. Historical release examples and external websites are outside this local link audit.

Executed examples covered the index/tree/pack/check/show CLI workflow, Python API, custom adapter, legacy body-checksum calculation, and exit 3 followed by a successful consistency check for an oversized pack. The source distribution was checked for all ten context documents and both build specifications. The full 66-test suite and Ruff also passed after the documentation changes. This follow-up does not add new semantic or LLM-quality claims.
