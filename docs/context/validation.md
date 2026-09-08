# Validation results

[English](validation.md) | [日本語](validation_ja.md)

This document summarizes the latest available validation results. Update the relevant results in place when checks are rerun; do not append a chronological history. Each check retains its verification date so that results from different runs are distinguishable.

## Validation summary

| Check | Latest verification | Result |
| --- | --- | --- |
| Local full suite, macOS / Python 3.12.10 | 2026-09-08 | 68 passed |
| Ruff (`uv run ruff check .`) | 2026-09-08 | Passed |
| GitHub Actions CI, Linux / Windows / macOS × Python 3.11 / 3.13 / 3.14 | 2026-09-07, on merge to `main` | All 9 jobs passed |
| Packet boundaries, approximately 40,000-line PL/SQL package | 2026-09-07 | No mid-line boundaries in 137 packets |
| Legacy output comparison against `d90beee330bca581d0a52eddec38362c3b28d50a` | 2026-09-05 | Byte-identical outputs for 7 fixtures |
| `build` output comparison against v0.3.0 samples | 2026-09-07 | Byte-identical except for the `original:` line in `parts/` |
| Source distribution and wheel build | 2026-09-05 | Passed |
| Wheel installed in a fresh Python 3.12.12 environment | 2026-09-05 | Version, mixed-language index, pack, check and legacy Java build passed |
| Documentation links, bilingual examples and distribution contents | 2026-09-05 | Passed; scope detailed below |

## Test coverage and output compatibility

The complete suite contains 68 tests: 30 legacy tests and 38 context-engine tests. Coverage includes exact whole-source reconstruction, Unicode and CRLF, multiple source languages, enclosing branch conditions and exception references, unresolved and ambiguous lexical calls, custom adapters and counters, oversized/opaque regions, context omission integrity, and CLI exit behavior.

Packet-boundary coverage includes a property test asserting that every packet starts at a line start and ends at a line end, and a regression test for a child whose raw span fits the budget but whose line-aligned span does not. Validation on a PL/SQL package of about 40,000 lines (budget 40,000 / reserve 4,000 bytes) found no mid-line boundaries in any of the 137 packets. Packet and oversized counts were unchanged by the line-alignment fix ([#27](https://github.com/elvezjp/code2map/issues/27)).

The seven legacy fixtures were `sample.py`, `sample.java`, `java8_syntax.java`, `large_file.py`, `function_only.py`, `empty.py`, and `comments_only.py`. The comparison used the same input paths for both versions and compared every generated file's bytes, including `INDEX.md`, `MAP.json`, and `parts/`.

Context-engine output samples are recorded under `context/` for each language in `docs/examples/v0.4.0/`.

## Dependencies and validation scope

The lockfile retains the existing dependency versions (Tree-sitter 0.25.2 and Java grammar 0.23.5). The fresh wheel installation additionally exercised Tree-sitter 0.26.0 with Java grammar 0.23.5. This is not an exhaustive dependency-version compatibility claim.

The CI results in the summary are hosted runs; the local suite result is from macOS. These tests establish structural and output contracts on fixtures, not complete Oracle/Java/Python semantic analysis or improved downstream LLM accuracy on production systems.

## Documentation verification

The documentation audit on 2026-09-05 covered 20 current root/context Markdown pages and 111 local links/heading references. Seven document pairs (root README, build specification and five context documents) have matching executable examples and language-switch navigation. Historical release examples and external websites are outside this local link audit.

Executed examples covered the index/tree/pack/check/show CLI workflow, Python API, custom adapter, legacy body-checksum calculation, and exit 3 followed by a successful consistency check for an oversized pack. The source distribution was checked for all ten context documents and both build specifications.
