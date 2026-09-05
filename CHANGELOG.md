[English](./CHANGELOG.md) | [日本語](./CHANGELOG_ja.md)

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Development version 0.4.0: a language-neutral source snapshot, structural hierarchy and lexical dependency graph, exposed through reusable Python APIs.
- `index`, `pack`, `check`, `tree`, and `show` commands for deterministic whole-source partitioning with enclosing context and explicit budget/parse statuses.
- PL/SQL, Python AST, and Java Tree-sitter context adapters; mixed-language directory input, strict encoding selection, source coverage and context integrity checks.
- Adapter and budget-counter protocols, context documentation, and regression tests. The existing `build` CLI and generated output contract are preserved.

### Changed

- Completed paired English/Japanese context documentation and build specifications; corrected command scope, development-branch setup, checksum definitions and CLI reference details.

- Added `python -m code2map` and `--version` entry points.
- Excluded deliberately non-executable generated fragments and malformed parser fixtures from Ruff checks.


## [0.3.0] - 2026-08-09

Addresses two advisories for the transitive development dependency `cryptography`, and retires the `versions/` directory in favour of git tags ([#17](https://github.com/elvezjp/code2map/issues/17)). There are no changes to the implementation or to the output of any command.

### Security

- **Raised the floor of `cryptography` to `>= 50.0.0`** to address [GHSA-g6cj-pr64-35w5](https://github.com/pyca/cryptography/security/advisories/GHSA-g6cj-pr64-35w5) / [CVE-2026-69247](https://nvd.nist.gov/vuln/detail/CVE-2026-69247) (High): PKCS#7 `EnvelopedData` decryption reported failures in distinguishable ways, exposing a Bleichenbacher oracle against the content-encryption key. Affects `>= 44.0.0, < 50.0.0`
  - Resolves Dependabot alert #13
  - Regenerated `uv.lock` (`cryptography` 49.0.0 → 50.0.0)
- Previously recorded under `[Unreleased]`: raised the floor of `cryptography` to `>= 48.0.1` to address [GHSA-537c-gmf6-5ccf](https://github.com/pyca/cryptography/security/advisories/GHSA-537c-gmf6-5ccf) (vulnerable OpenSSL bundled in `cryptography` wheels `< 48.0.1`)
  - Added a `[tool.uv]` `constraint-dependencies` entry in `pyproject.toml`
  - Superseded by the `>= 50.0.0` constraint above; both advisories are covered by the single constraint now in place
- **The runtime is unaffected by either advisory**: `cryptography` is only pulled in via `twine` → `keyring` → `SecretStorage` on Linux, all of which are development dependencies. code2map itself depends only on `tree-sitter` and `tree-sitter-java`, and does not use the PKCS#7 APIs
  - The alert is reported against `uv.lock`, which resolves the full development environment. Users installing code2map do not receive `cryptography`

### Changed

- **Moved version management to git tags** ([#17](https://github.com/elvezjp/code2map/issues/17)): Removed the `versions/` directory that kept snapshots of older versions; only the latest code is now kept at the repository root
  - Snapshots of old versions (v0.1.1–v0.2.0) are preserved under `versions/` in the `v0.2.1` tag. That tag is the archive reference point for the old layout and must not be deleted or moved
  - Resolves duplicate Dependabot alerts caused by lockfiles under `versions/`, where the same advisory was reported once per archived manifest
  - No tags were created retroactively for v0.1.1–v0.2.0. The version recorded in `pyproject.toml` moves back and forth across the history (for example `0.2.0` at `61b5887` predates `0.1.2` at `03448d7`), so the commit corresponding to each release cannot be identified reliably
  - Added a "Version Management" section to the README (EN/JA) and updated the Dependabot alert policy in SECURITY (EN/JA)
- Removed `/versions` from the sdist exclude list in `pyproject.toml`

### Added

- **Output samples for v0.3.0** under `docs/examples/v0.3.0/` (Java and Python), regenerated with this version
  - Identical to the v0.2.1 samples apart from the `original:` line in each `parts/` file, which records the input path. `INDEX.md` and `MAP.json` are byte-for-byte identical, confirming that this release does not change the output
  - Added a note to `docs/examples/README.md` explaining that output is deterministic (static analysis only, no LLM, no timestamps in the output)

## [0.2.1] - 2026-05-12

### Changed

- **Bumped minimum Python version from 3.9 to 3.11** ([#14](https://github.com/elvezjp/code2map/issues/14))
  - `pyproject.toml`: `requires-python = ">=3.11"`, removed `Python :: 3.9` / `Python :: 3.10` from classifiers
  - CI matrix updated: `["3.9", "3.12"]` → `["3.11", "3.13"]`
  - README / CONTRIBUTING / spec.md updated to require Python 3.11+

### Added

- **PyPI packaging metadata** ([#12](https://github.com/elvezjp/code2map/issues/12))
  - Extended `[project]`: contact email in `authors`, `keywords`, additional `classifiers` (`Development Status :: 3 - Alpha`, `Intended Audience :: Developers`, `Topic :: Software Development :: *`, `Python :: 3 :: Only`)
  - Added `[project.urls]`: `Homepage`, `Documentation`, `Changelog`, `Issues`
  - Added `build` / `twine` to `[project.optional-dependencies].dev`
  - Configured `[tool.hatch.build.targets.wheel]` and `[tool.hatch.build.targets.sdist]` with explicit include/exclude (excludes `versions/`, `docs/`, `main.py`, `.github/`)

### Fixed

- Aligned `code2map.__version__` with `pyproject.toml` version (was left at `"0.2.0"`)

### Security

- **Resolved Dependabot alert [#2](https://github.com/elvezjp/code2map/security/dependabot/2)**: pytest now resolves to 9.0.3 (fixes CVE-2025-71176, Medium 6.8). Previously, with `requires-python = ">=3.9"`, pytest 8.4.2 was pinned because pytest 9.x requires Python 3.10+.

### Notes

- Saved v0.2.0 snapshot to `versions/v0.2.0/`

## [0.2.0] - 2026-03-12

### Changed

- **Replace Java parser with Tree-sitter**: Fully replaced `javalang` with `tree-sitter` + `tree-sitter-java` ([#9](https://github.com/elvezjp/code2map/issues/9))
  - Java 8+ syntax (lambda expressions, method references `Type[]::new`, etc.) now parses correctly
  - On syntax errors, returns a warning with the error line number (partial parse results are returned)
  - Future syntax (records, sealed classes, switch expressions, etc.) can also be supported

### Added

- **Tests**: Added tests for correct parsing of Java 8+ syntax and warning return on parse errors

### Changed (Dependencies)

```diff
- javalang>=0.13.0
+ tree-sitter>=0.21.0
+ tree-sitter-java>=0.21.0
```

- Saved v0.1.3 snapshot to `versions/v0.1.3/`

## [0.1.3] - 2026-03-12

### Fixed

- **Java parse error message improvement**: Fixed an issue where the error message was empty when parsing failed on files containing Java 8+ syntax ([#9](https://github.com/elvezjp/code2map/issues/9))
  - Now uses `description` and `at` attributes of `JavaSyntaxError` to output the cause and location of the error
  - Before: `"Java parse error: "` (empty)
  - After: `"Java parse error: Expected '.' (at Keyword "new" line N, position M)"`

### Added

- **Tests**: Added 3 test cases for Java parse error messages
- **Test fixture**: Added a Java file containing Java 8+ syntax (method reference `Type[]::new`)

### Changed

- Saved v0.1.2 snapshot to `versions/v0.1.2/`

## [0.1.2] - 2026-02-25

### Fixed

- **Filename sanitization**: parts/ filenames now strip Windows-reserved characters (`< > : " / \ | ? *`) ([#5](https://github.com/elvezjp/code2map/issues/5))
  - Java constructor `<init>` filename changed from `User_<init>.java` to `User_init.java`
  - Resolves `git clone` failures on Windows environments
  - Collisions caused by sanitization are still resolved by the existing hash-suffix mechanism

### Added

- **Tests**: Added 3 test cases for filename sanitization

### Changed

- Regenerated sample output files (`docs/examples/java/output/`)
- Added filename sanitization specification to `spec.md`
- Saved v0.1.1 snapshot to `versions/v0.1.1/`

## [0.1.1] - 2026-02-06

### Added

- **Symbol ID feature**: Assigns a unique identifier to each symbol
  - `--id-prefix`: Allows specifying the symbol ID prefix (default: `CD`)
  - INDEX.md: Displays IDs before symbol names in `[CD1]` format
  - MAP.json: Added `id` field at the top
  - parts/: Added `id: CD1` line to headers

- **Tests**: Added tests for the ID feature

### Changed

- Added `id` field to the Symbol model

## [0.1.0] - 2026-01-27

Initial release. MVP version supporting both Python and Java.

### Added

- **CLI command**: Implemented `code2map build` command
  - `--out`: Specify the output directory
  - `--lang`: Explicitly specify the language (auto-detected from extension if omitted)
  - `--verbose`: Output detailed logs
  - `--dry-run`: Display the plan only without generating files

- **Python parser**: Analysis using the `ast` module
  - Supports extraction of classes, methods, and functions
  - Supports docstring extraction
  - Supports call relationship inference
  - Supports import information collection

- **Java parser**: Analysis using the `javalang` library
  - Supports extraction of classes, methods, and fields
  - Supports Javadoc extraction
  - Supports call relationship inference
  - Supports nested classes, constructors, and overloads

- **INDEX.md generation**: Markdown index with class/method/function list and roles
  - Display of call relationships (Calls)
  - Detection and description of side effects (Side Effects)
  - Embedding of warnings (`[WARNING]`)

- **parts/ generation**: Split source code by class/method units
  - Metadata header attachment
  - Language-specific comment prefix support
  - Hash suffix for collision avoidance

- **MAP.json generation**: Machine-readable mapping table (JSON format)
  - Complete mapping of symbol information
  - SHA-256 checksum calculation

- **Tests**: Unit tests, e2e tests, and edge case tests

- **CI/CD**: Automated testing via GitHub Actions (Python 3.9–3.12)

### Known Limitations

This version has the following limitations:

- Single file only (directory-level analysis not yet supported)
- Static analysis only (dynamic dispatch and reflection are not considered)
- Class/method-level splitting only (processing phase-level splitting not supported)
- Supported languages: Java and Python only

## Links

- [Repository](https://github.com/elvezjp/code2map)
- [Issue Tracker](https://github.com/elvezjp/code2map/issues)

[0.3.0]: https://github.com/elvezjp/code2map/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/elvezjp/code2map/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/elvezjp/code2map/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/elvezjp/code2map/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/elvezjp/code2map/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/elvezjp/code2map/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/elvezjp/code2map/releases/tag/v0.1.0
