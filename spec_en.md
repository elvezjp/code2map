# `build` command specification

[English](spec_en.md) | [日本語](spec.md)

This document describes the existing `build` workflow retained in the 0.4.0 development version. For `index` / `pack` / `check` / `tree` / `show` and the Python API, see the [context guide](docs/context/README.md) and [data contracts](docs/context/contracts.md). A legacy `MAP.json` cannot be used as input to `pack`.

## 1. Purpose and scope

Extract classes, methods and functions from one Python or Java file and generate an index, fragments and source-line mappings. This supports structural inspection of large files, focused reviews and references back to source.

Fragments are not intended for compilation or execution. Import completion, runtime dependency resolution, dynamic analysis, replacement of formatters/linters and generation of guaranteed-correct design documents are outside scope. Calls and side effects are static candidates or heuristics.

Class fragments include method bodies and overlap method fragments. Top-level imports and constants may not be extracted. `build` does not guarantee complete source coverage or an input budget. Use `index` / `pack` for those workflows.

## 2. Input and environment

| Item | Specification |
| --- | --- |
| Input | One source file |
| Languages | Python `.py`, Java `.java`; explicit `--lang` override available |
| Encoding | UTF-8 assumed; undecodable bytes become U+FFFD with a warning |
| Newlines | Source is split into lines and fragment bodies joined with LF; original newline bytes are not retained |
| Python | 3.11 or higher |
| Dependencies | `tree-sitter`, `tree-sitter-java` |
| OS | Intended for Windows/macOS/Linux; see the [validation record](docs/context/validation.md) for verified environments |

The workflow targets reviews of files with thousands of lines, but does not guarantee runtime or memory limits for every input. Source and syntax trees are held in memory. `build` handles one file; directory indexing is implemented in the context engine.

## 3. CLI

```text
code2map build input_file [--out DIR] [--lang {java,python}]
               [--id-prefix PREFIX] [--verbose] [--dry-run]
```

| Argument/option | Required | Default | Meaning |
| --- | --- | --- | --- |
| `input_file` | Yes | — | File to analyze |
| `--out` | No | `./code2map-out` | Output directory |
| `--lang` | No | Detect from extension | `java` or `python` |
| `--id-prefix` | No | `CD` | Symbol ID prefix |
| `--verbose` | No | false | Detailed logging |
| `--dry-run` | No | false | Print symbols and planned outputs without writing |

An unknown extension without `--lang` is an error. `--help` prints help. Top-level `code2map --version` prints the package version.

| Exit code | Meaning |
| --- | --- |
| 0 | Successful operation without warnings |
| 1 | Fatal errors such as missing input or undetectable language |
| 2 | Generation or dry-run completed with parser warnings; argparse also uses 2 for invalid CLI arguments |

Syntax errors normally yield results with warnings. A Python parse failure returns no symbols; Java returns symbols it can extract. Parse failures do not uniformly use exit code 1.

Output parent directories are created and files generated with the same names are overwritten. Other files and stale fragments are not removed. Use a fresh output directory if it must contain only the current results. Unexpected I/O errors may terminate with a Python exception.

## 4. Outputs

### 4.1 `INDEX.md`

The first heading is `# Index: <filename>`. Warnings use `<!-- [WARNING] ... -->`. `Classes`, `Methods` and `Functions` sections are generated when their respective symbols exist.

Each entry includes ID, display name, start/end lines and relative fragment path. Method names use `ClassName#methodName`. Method/function entries add the following fields only when information exists; class entries do not include these extra fields.

| Field | Contents |
| --- | --- |
| `role` | First line derived from Docstring/Javadoc, shortened at its first period |
| `calls` | Call names extracted from the syntax tree |
| `side effects` | Keyword-based side-effect candidates from the target body |

Fragment references are emitted as `-> parts/...` text.

### 4.2 `parts/`

| Kind | Filename |
| --- | --- |
| Class | `<ClassName>.class.<ext>` |
| Method | `<Parent>_<methodName>.<ext>` |
| Function | `<functionName>.<ext>` |

Nested classes use the class name supplied by the parser; they are not always expanded to `Outer_Inner`. Qualified names and parent information are stored in the internal Symbol. Characters `< > : " / \ | ? *` are removed from filenames. For example, a Java `<init>` constructor becomes `User_init.java`. Logical names and header display names such as `User#<init>` are unchanged.

If a candidate filename has already been used, append `__abcd`, using the first four SHA-256 hex characters of the signature, or `display-name_start-line` when no signature exists. The first symbol with a given filename has no suffix. This short hash does not guarantee collision avoidance for every possible input.

Headers use `#` for Python and `//` for Java and record:

- `code2map fragment (non-buildable)`
- `id`: prefix plus a one-based counter in parser-returned order, such as `CD1`
- `original`: original source path
- `lines`: original start–end lines, one-based and inclusive
- `symbol`: display name
- `notes`: import-derived references and call names, when present

One newline separates the header from the extracted body, followed by a final newline. No additional blank line is inserted.

### 4.3 `MAP.json`

The CLI emits a JSON array with assigned IDs, in parser symbol order.

| Field | Type | Contents |
| --- | --- | --- |
| `id` | string | Prefix plus counter; omitted when the generator is called directly without IDs |
| `symbol` | string | Symbol display name |
| `type` | string | `class`, `method` or `function` |
| `original_file` | string | Original file basename |
| `original_start_line` | integer | One-based starting line |
| `original_end_line` | integer | Inclusive ending line |
| `part_file` | string | Relative path beginning with `parts/` |
| `checksum` | string | SHA-256 of the body described below, 64 lowercase hexadecimal characters |

The checksum covers **only the extracted body**, excluding the generated metadata header and appended final newline. Source is read with `splitlines()`, the selected lines are joined with `"\n".join(...)`, and that string is encoded as UTF-8 for hashing. This differs from hashing the entire generated fragment file.

```python
import hashlib
from pathlib import Path

lines = Path("examples/pricing.py").read_text(encoding="utf-8", errors="replace").splitlines()
start_line, end_line = 1, 3  # Replace with the range recorded in MAP.json.
fragment = "\n".join(lines[start_line - 1:end_line])
checksum = hashlib.sha256(fragment.encode("utf-8")).hexdigest()
```

## 5. Processing and language support

Processing consists of input checks, language detection, parser selection, symbols/warnings, ID assignment, fragment generation, INDEX generation and MAP generation. Dry-run prints symbols and planned files in place of writing them.

Parsers return Symbols with name, kind, line range, parent, qualified name, role, call names and import-derived dependencies. Internal fields are defined in `code2map/models/symbol.py`.

| Element | Python AST | Java Tree-sitter CST |
| --- | --- | --- |
| Classes and nested classes | Extracted | Extracted |
| Methods | Extracted | Extracted |
| Top-level functions | Extracted, including async | Not applicable |
| Nested functions | Included in parent, without separate fragments | Not applicable |
| Constructors | Ordinary methods | Extracted as `<init>` |
| Interface/enum/record/annotation types | Not applicable | Extracted as class kind |
| Decorators/annotations | Python decorator lines are excluded from fragment spans | No detailed semantic analysis |
| Fields | Not extracted as independent symbols | Not extracted as independent symbols |
| Lambdas, method references, etc. | Syntax accepted by the running AST | Java 8+ syntax accepted by the grammar |

Python obtains call names from `ast.Call`; Java uses `method_invocation`. Java Javadoc comes from preceding CST comments. Java line ranges come from CST positions; parse errors return line/column warnings and available symbols. Type inference, complete generic binding, indirect call targets, reflection and dynamic dispatch are not resolved.

## 6. Side effects and diagnostics

Side-effect detection lowercases the body and looks for fixed substrings. This table gives examples; see `code2map/generators/index_generator.py` for the full rules.

| Output category | Example substrings |
| --- | --- |
| `file io` | `open(`, `filewriter`, `outputstream`, `write(`, `path` |
| `stdout` | `print(`, `system.out`, `stderr` |
| `logging` | `logging.`, `logger.`, `log.` |
| `network` | `http`, `socket`, `request`, `client` |
| `db` | `jdbc`, `select `, `execute(`, `save`, `commit` |
| `exceptions` | `throw new`, `raise ` |

False positives and missed effects are possible. These rules do not prove runtime side effects or reachability. Configuration-file customization is not implemented.

Warnings appear in INDEX and stderr, not MAP. Warnings are displayed even without `--verbose`. Empty symbol results still generate an INDEX and an empty MAP array. Replacement decoding and warnings differ from the context engine's strict decoding.

## 7. Extension policy

Existing parser extensions return symbols and warnings from `BaseParser.parse(file_path)`. Context-engine languages use the separate `Adapter` contract. These are different interfaces.

Version 0.4.0 adds multiple-file indexing and budgeted structural partitioning through the context engine. See [supported behavior and remaining work](docs/context/limitations.md) for priorities. Configuration files, incremental analysis, additional languages, call-graph visualization, CI templates for automatic index generation, a Web UI and IDE integration remain extension candidates, distinct from implemented features.

Preserve the existing INDEX/MAP/parts output contract, isolate language-specific code and keep new behavior explicitly selectable.
