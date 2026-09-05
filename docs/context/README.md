# Context engine — 0.4.0 development

[English](README.md) | [日本語](README_ja.md)

code2map now separates **indexing the entire source** from **packing a portion with its context**. This engine can be reused by review, documentation, migration, and LLM tools without coupling to a model provider. The code is distributed under the repository's MIT license.

## From 0.3.0

| Workflow | Command | Output |
| --- | --- | --- |
| Existing class/function extraction | `build file.py --out output` | Unchanged `INDEX.md`, `MAP.json`, `parts/` |
| Whole-source structural indexing | `index file-or-directory --output index.json` | Schema-1 source snapshot, hierarchy, lexical relation candidates |
| Context-aware partitioning | `pack index.json --output pack.json` | Schema-1 packets with exact targets and supporting context |

`build` continues to support Python and Java. It intentionally produces overlapping class/method fragments. The new engine supports Python, Java, and PL/SQL and covers every indexed source exactly once across packet targets. It does not rewrite source files or generate compilable modules. A legacy `MAP.json` is not an index snapshot; re-index the original sources to use `pack`.

## CLI

Check out the development branch using the [root README](../../README.md), then run these commands at the repository root. Replace `NODE_ID` with an ID printed at the end of a `tree` output line.

```bash
uv sync --locked --all-extras
uv run code2map index examples --output output/index.json
uv run code2map tree output/index.json --depth 3
uv run code2map pack output/index.json --output output/pack.json \
  --budget-bytes 16000 --reserve-bytes 2000 --dependency-limit 8
uv run code2map check output/index.json --pack output/pack.json
uv run code2map show output/index.json NODE_ID
```

`index` accepts a file or recursively selected supported files in a directory. Extensions: `.py`, `.java`, `.sql`, `.pks`, `.pkb`, `.pls`, `.plsql`. Hidden paths and `node_modules`, `__pycache__`, `build`, and `dist` directories are excluded. Unsupported files are skipped. It uses strict UTF-8 by default; select `--encoding cp932` or another supported encoding for legacy assets. Index snapshots contain the complete decoded source text.

### Arguments and defaults

| Command | Arguments/options | Behavior |
| --- | --- | --- |
| `index` | `input`, `--output PATH` | Both required; output name must end in `.json` |
| `index` | `--encoding` | Default `utf-8`; also `utf-8-sig`, `cp932`, `shift_jis`, `euc_jp` |
| `pack` | `index`, `--output PATH` | Both required; output name must end in `.json` |
| `pack` | `--budget-bytes` | Default `16000`; positive integer |
| `pack` | `--reserve-bytes` | Default `0`; nonnegative and below budget |
| `pack` | `--dependency-limit` | Default `8`; nonnegative limit on optional supporting excerpts |
| `check` | `index`, `--pack PATH` | Index required; supply `--pack` to validate packets too |
| `tree` | `index`, `--depth` | Index required; depth defaults to `3`, must be nonnegative; file root is depth 0 |
| `show` | `index`, `node_id` | Both required; prints provenance followed by node source |

Use `--help` on each command and `--version` at the top level. Output parent directories are created automatically and existing output JSON is replaced. `index` refuses to overwrite an indexed source; `pack` refuses to overwrite its input index.

### Exit codes and packet handling

For context commands, exit codes are 0 for successful operations, 2 for invalid input or validation failure, and 3 when indexing reports diagnostics or packing produces opaque/oversized packets. A partial artifact is still written on exit 3. `check` returns 0 when a partial artifact is internally consistent; this does **not** mean all its packets are ready. See the [build specification](../../spec_en.md) for its existing exit codes.

Each `packets[i].payload` is a JSON string ready for the caller to pass as source data. The CLI counts this entire string in **UTF-8 bytes, not tokens**. `reserve` subtracts space for caller instructions, chat framing, and output. It is the caller's responsibility to choose an adequate reserve. `omitted_context` lists supporting excerpts excluded by budget or count; relation IDs remain inside the payload. Inspect status and omissions before dispatching a packet.

## Python API

```python
from code2map import build_index, pack_index, validate_index, validate_pack

index = build_index("examples")
validate_index(index)
packed = pack_index(index, budget=16000, reserve=2000)
validate_pack(index, packed)
for packet in packed["packets"]:
    if packet["status"] == "ready":
        payload = packet["payload"]
        # The caller decides whether its available context is sufficient.
```

Supply a model-specific counter through the API:

```python
class ModelTokens:
    def __init__(self, tokenizer, identity):
        self.tokenizer = tokenizer
        # Include the tokenizer implementation, vocabulary revision and options.
        self.identity = identity

    def count(self, text):
        return len(self.tokenizer.encode(text, add_special_tokens=False))

# counter = ModelTokens(your_tokenizer, "your-pinned-tokenizer-revision")
# packed = pack_index(index, budget=8192, reserve=2048, counter=counter)
# validate_pack(index, packed, counter=counter)
```

The API accepts trusted custom language adapters through `build_index(..., adapters=[...])`, replacing built-ins. Protocols and data classes are exported from `code2map.context`: `Adapter`, `BudgetCounter`, `Node`, `Parsed`, `Reference`, `UTF8Bytes`. See the [data contract](contracts.md) for node kinds and offsets.

## Guarantees and limits

- Source snapshots preserve decoded text, CRLF, comments and whitespace. Offsets are zero-based Unicode characters, end-exclusive; displayed lines are one-based. See the [data contract](contracts.md) for differences from the original encoded bytes.
- With fixed relative paths, source bytes, encoding, Python/runtime/adapter versions, packing settings and counter behavior, output is deterministic. No timestamps or absolute paths are included. IDs change when their source changes; they are not persistent across edits.
- Targets cover every indexed source once, while supporting context may overlap. Validators check coverage, exact excerpts, mandatory headers and relations, payload hashes, budgets, dependency omissions and statuses. Hashes are integrity checks, not authenticated signatures.
- Budget compliance applies to the serialized payload. Indivisible statements, very long headers and opaque regions can be oversized. They remain intact and are never silently truncated.
- `candidate` and `ambiguous` are lexical evidence, not proven runtime binding or data flow. Qualified external calls can remain unresolved. A `ready` status asserts size and reported diagnostics, not complete program understanding.
- The PL/SQL scanner is not the Oracle grammar or compiler. Unsupported units are retained with diagnostics when detected; structurally accepted code is not proof of Oracle validity.
- Java uses Tree-sitter and records both parser and grammar versions. Syntax errors make the file opaque. Expressions, anonymous classes and lambdas are not recursively partitioned. Do-while remains indivisible so its trailing condition cannot be lost. Type inference, imports, inheritance and dynamic dispatch are not resolved.
- Python uses the running interpreter's AST. Imports are not executed. Dynamic language features and full `global`/`nonlocal` binding analysis are not implemented.

See [architecture](architecture.md), [contracts](contracts.md), and [language limitations](limitations.md) for more detail.

## Development

```bash
uv run pytest
uv run ruff check .
uv build
```

The test suite combines legacy output behavior with whole-source coverage, Unicode/CRLF, branch and exception context, ambiguous dependencies, opaque/oversized regions, custom adapters/counters, persisted artifact validation, and public CLI entry points.

See the [validation record](validation.md) for the checked environments and compatibility comparison.
