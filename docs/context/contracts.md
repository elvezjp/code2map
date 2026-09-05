# Data contracts and extensions

[English](contracts.md) | [日本語](contracts_ja.md)

## Positions

All `start` and `end` fields are **zero-based Unicode character offsets into decoded source, with an exclusive end**. They are not byte offsets. Displayed line numbers are one-based. CRLF remains two characters. Python AST and Java CST byte offsets are converted to character offsets.

## Index schema 1

| Field | Contents |
| --- | --- |
| `schema_version` | `1`, independently of the package version |
| `generator`, `runtime`, `adapters` | Generator, Python runtime and adapter versions |
| `sources` | `id`, `path`, `encoding`, `original_sha256`, `text_sha256`, `text`, `adapter` |
| `nodes` | `id`, `source_id`, `parent_id`, `kind`, `name`, `symbol`, `start`, `end`, `header_end`, `start_line`, `end_line`, `confidence` |
| `edges` | `id`, `owner_id`, `source_id`, `start`, `end`, `kind`, `symbol`, `target_ids`, `resolution`, `evidence` |
| `diagnostics` | `source_id`, `start`, `end`, `code`, `message` |

Each source has one covering file root. Siblings do not overlap and children lie within their parent. Adapters need not register whitespace or comments as nodes; the partitioner preserves those gaps.

`original_sha256` hashes the original bytes; `text_sha256` hashes the decoded text encoded as UTF-8. For example, decoding with `utf-8-sig` removes the BOM from stored text. Text reconstruction therefore preserves the decoded source, not necessarily the original encoded bytes.

Edge kinds are `call`, `reference` and `jump`. Resolution is `candidate` for one target, `ambiguous` for multiple targets, and `unresolved` for none. Source evidence ranges are retained. Unresolved calls/jumps are retained; ordinary references without candidates are omitted from the graph. Name matching is not semantic resolution or proof of reachability.

## Pack schema 1

The top level contains `schema_version`, `index_sha256`, `policy`, `packets` and `summary`. `policy` records algorithm, counter identity, budget, reserve and dependency excerpt limit. The package version and these schema versions are independent.

Each packet has `id`, `source_id`, `start`, `end`, `status`, `budget_used`, `payload_sha256`, a serialized `payload` string and `omitted_context`.

Payload fields:

- `index_sha256`: identifies the locked input snapshot.
- `instruction`: states the target scope and interpretation limits.
- `target`: exact source excerpt; targets cover every indexed source once.
- `enclosing_context`: original headers of structures enclosing the target.
- `relations`: candidates with evidence positions inside the target. Edges with equal kind, symbol, target IDs and resolution are grouped; `occurrences` retains every `[start, end]`. Relations are not removed to save budget.
- `exception_regions`: references to enclosing exception regions; consumers must assess applicability.
- `dependency_context`: optional declarations or signatures; a callee's full body is not necessarily attached.
- `diagnostics`: reported parse problems intersecting the target.

Statuses are `ready`, `opaque` and `oversized`. If a region is both unknown and too large, its status is `oversized`, with parse problems still recorded in payload diagnostics. `ready` means no reported diagnostic intersects the target and the payload fits; it does not establish complete semantic understanding.

`omitted_context` is outside the payload. It records `node_id` and `reason` (`budget` or `dependency_limit`). Consumers should inspect it along with relations before sending a payload to an LLM. `summary` counts packets and each status.

`payload_sha256` hashes the exact payload string. Reformatting changes it. Budget validation measures that same complete string. `index_sha256` hashes the canonical index serialization: sorted JSON keys, two-space indentation, unescaped Unicode and a final LF.

## Language adapters

Pass objects implementing `code2map.context.Adapter` to `build_index(..., adapters=[...])`. This list replaces the built-ins.

```python
from code2map.context import Node, Parsed

class WholeFileAdapter:
    name = "my-language"
    version = "1"
    extensions = (".example",)

    def parse(self, text, path):
        return Parsed(Node("file", 0, len(text), path, 0,
                           children=[Node("opaque", 0, len(text),
                                          confidence="unknown")]),
                      diagnostics=[{"code": "UNSUPPORTED_SYNTAX",
                                    "message": "Parser not implemented",
                                    "start": 0, "end": len(text)}])
```

Once syntax is supported, return positioned children and `Reference(kind, symbol, start, end)`. Common scope kinds are `file`, `package_body`, `package_spec`, `function`, `procedure`, `class` and `block`. Other kinds express interval hierarchy.

`header_end` marks the end of source needed as enclosing context. Including an entire body can make every split payload large. Unrecognized regions must have both an `opaque` node and diagnostics.

Custom adapters execute as trusted Python code; code2map does not sandbox them.

## Counters

Implement `identity: str` and `count(text) -> int`, returning a nonnegative integer. Behavior must be deterministic. Include implementation, vocabulary revision and configuration in the identity, and supply the same implementation during validation. A different identity is rejected. The default `UTF8Bytes` counter counts UTF-8 bytes; it is not a token estimate.
