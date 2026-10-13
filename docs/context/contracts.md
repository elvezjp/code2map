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

Each source has one covering file root. Siblings do not overlap and children lie within their parent. Adapters need not register whitespace or comments as nodes; the partitioner preserves those gaps. When the partitioner splits a range at child boundaries it aligns each boundary to whole lines, so a child that begins after indentation or ends before a trailing comment never leaves a partial line in the neighbouring range; when two children share one line, the earlier child keeps that line.

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

Once syntax is supported, return positioned children and `Reference(kind, symbol, start, end)`. Common scope kinds are `file`, `package_body`, `package_spec`, `namespace`, `function`, `procedure`, `class` and `block`; `namespace` also qualifies the names below it. Other kinds (for example `control`, `branch`, `handler`, `label`, `preproc`) express interval hierarchy only.

`header_end` marks the end of source needed as enclosing context. Including an entire body can make every split payload large. Unrecognized regions must have both an `opaque` node and diagnostics.

Custom adapters execute as trusted Python code; code2map does not sandbox them.

## Counters

Implement `identity: str` and `count(text) -> int`, returning a nonnegative integer. Behavior must be deterministic. Include implementation, vocabulary revision and configuration in the identity, and supply the same implementation during validation. A different identity is rejected. The default `UTF8Bytes` counter counts UTF-8 bytes; it is not a token estimate.

## Contracts added in the next version (not yet implemented)

This chapter specifies contracts to be added in the next version. **They are not implemented yet.** Index schema 1 and Pack schema 1 above are the contracts of the current version and remain in effect until this is implemented.

The next version handles section headings written by authors in comments, ranges that parse fine but deserve attention, and diagnostics of the partitioning result. All of them are implemented as **mechanisms independent of language and writing style**; values specific to a writing style (separator shapes, change-history formats, disabling conventions, and so on) are supplied from outside through a profile (below). Without a profile, no headings and no style-dependent annotations are produced.

### Profiles

A profile is a TOML file that supplies the writing-style rules of the sources. Pass it with `index --profile PATH`.

- `index` validates the profile and stores its normalized content and SHA-256 in the index as `profile`. `pack`, `report`, and `check` use the profile stored in the index and do not accept another one (so the index and the partitioning rules cannot drift apart).
- Unknown keys, wrong types, and regular expressions that fail to compile stop with exit code 2 before the index is written.
- The implementation holds no writing-style values as defaults. Without a profile, `headings` is empty and style-dependent annotations (`DISABLED_REGION`, `HEADING_FALLBACK`) are not produced.

| Key | Meaning |
| --- | --- |
| `profile.id` | User-chosen profile name (recorded in the index) |
| `headings.separator` | Regular expression for line comments treated as separators (for example, a line repeating one symbol at least N times) |
| `headings.title_skip` | Regular expression for lines skipped while looking for a heading title (for example, change-history lines or decoration-only lines) |
| `headings.title_exclude` | Regular expression for titles that are not headings |
| `headings.indent_from` | Which line gives the heading indentation (`title` = title line, `separator` = separator line) |
| `headings.tab_indent` | Handling of headings whose indentation contains tabs (`fallback` = not indexed, annotated instead) |
| `markers.change` | Regular expression for change-history lines (for example, comment lines marking the start and end of a modification). Used as a stop position when raising cut points and counted in diagnostics |
| `annotations.disabled_region` | Rule for ranges treated as disabled code (for example, block comments starting at column 0). Annotated only when supplied |
| `report.*` | Default diagnostic thresholds (command arguments override them) |

### Additional language-adapter capability

Detecting comment headings needs the ranges of comments and literals. An adapter may provide the optional capability `lex(text)`, which returns the ranges of line comments, block comments, and string literals. For sources whose adapter has no `lex`, no headings and no style-dependent annotations are produced. Partitioning and recomputation branch on this capability, not on adapter names.

The PL/SQL adapter provides `lex` first.

### Index schema 2

Adds the following to Index schema 1.

| Field | Contents |
| --- | --- |
| `schema_version` | `2` |
| `profile` | `null` or `{id, sha256, content}` (normalized profile) |
| `headings` | `id`, `source_id`, `owner_id`, `parent_heading_id`, `start`, `end`, `title_start`, `title_end`, `section_end`, `start_line`, `title_line`, `indent`, `style`, `title` |

A heading is a procedural section break written by the author in comments; it lives outside the syntax tree. Nodes and unit ranges are not changed for headings.

- **Detection**: a comment-only title line immediately after a separator matching the profile's `headings.separator` is a heading. Lines matching `headings.title_skip` are skipped; a separator, a code line, or a blank line ends the search. Separators drawn inside block comments or strings are not headings.
- **Owner**: `owner_id` is the innermost function or procedure (a kind treated as a scope) containing the band. Headings outside every unit are not indexed.
- **Range**: `start`/`end` is the band (from the start of the upper separator line through the title line and, if paired, the end of the lower separator). A heading that shares its upper separator with the previous heading starts its band at the title line. Bands of the same owner do not overlap. `title_start`/`title_end` is the title line (without the line break); `title` is the text with comment markers and surrounding spaces removed.
- **Hierarchy**: `parent_heading_id` is the most recent heading with shallower indentation in the same owner; top level is `null`. `section_end` is the `start` of the next heading at the same or a shallower depth, or the end of the owner. The hierarchy is the author's table of contents, not proof of control flow.
- **ID**: `identity("heading", source_id, owner_id, start, end)`. The same title at a different position gets a different ID.
- **Validation**: headings are recomputed from the pinned source text and the stored profile and compared with the stored headings.

The next version's `check`, `pack`, and `report` explicitly reject schema 1 indexes (no silent completion). Rebuild them with `index`.

### Pack schema 2

Adds the following to Pack schema 1.

- **`policy.algorithm`**: either `structural-greedy-v1` (the current method, default) or `structural-heading-v1` (heading-first partitioning with raised cut points; see [Architecture](architecture.md)). Select it with `pack --algorithm`. The default does not change, so existing users get the same output.
- **`policy.profile_sha256`**: hash of the profile stored in the index (`null` if none).
- **Packet ID**: `identity("packet-v2", index_sha256, canonical(policy), source_id, start, end)`. Changing any policy field changes every packet ID. Do not reuse earlier packet IDs in a new run.
- **Headings in `enclosing_context`**: headings whose span `[start, section_end)` overlaps the target, and their ancestors, are added as excerpts with `role: section-heading` (with `heading_id`, `owner_id`, `parent_heading_id`, and the same position fields as other excerpts). Heading excerpts may overlap the target and count toward the budget.
- **`annotations`**: ranges intersecting the target that parse fine but deserve attention. Separate from diagnostics; they do not affect packet status. Each element has `id`, `source_id`, `kind`, `start`, `end`, `start_line`, `end_line`, and `message`. Ranges stay as they are in the source and are not clipped to the packet range. Intersection uses half-open intervals. Annotations are part of the payload and count toward the budget.

| kind | Meaning | When |
| --- | --- | --- |
| `SOURCE_LONE_CR` | A CR not followed by LF. Line numbers are LF-based, so this character does not advance the line | All languages, always |
| `DISABLED_REGION` | A range treated as disabled code. The source stays in the target; no nodes, edges, or diagnostics are produced. It is an annotation based on the profile's convention and does not guarantee that the range is really unused | When `annotations.disabled_region` is supplied. Not added to sources whose lexing failed |
| `HEADING_FALLBACK` | A heading band that cannot be used as a partition boundary (indentation with tabs, inside a statement, declaration, or syntax header, and so on) | With `structural-heading-v1` |

- **Validation**: the partition plan is recomputed from the same index, policy, and counter and must match the sequence of packet ranges.

The next version's `check` and `report` explicitly reject schema 1 packs. Rebuild them with `pack`.

### Report schema 1 (partitioning diagnostics)

`report INDEX --pack PACK --output DIR` writes `report.json` (the machine-readable record) and `report.md` (for people) as derivatives of the pack. It does not change the index, the pack, or packet IDs. Thresholds only choose what to list. The same index, pack, and thresholds produce the same `report.json` (no timestamps or absolute paths). `report.md` does not contain source bodies (it does contain line numbers and heading titles). Select the language of `report.md` with `--lang en|ja` (default `en`).

Top-level fields: `schema_version` (`1`), `generator`, `index_sha256`, `pack_sha256`, `policy`, `pack_summary`, `thresholds`, `attribution_defaults`, `counts`, `counts_by_attribution`, and `findings`.

Each finding has:

- `code`
- `attribution_default`: initial cause. `source` (writing style of the source) / `rule` (partitioning rule) / `budget` / `mixed` / `unknown`. It is a per-kind default, not a cause determined by the machine.
- `attribution_override`: a field for people to override the cause; `null` when generated.
- `source_id`, `path`, `start`, `end`, `start_line`, `end_line`, `lines`, `bytes`
- `unit`: the owning function or procedure; `null` outside units or across several.
- `reason`: fixed text with numbers.
- `measures`: per-kind numbers.
- `refs`: `packet_ids`, `heading_ids`, `annotation_ids`, `node_ids`.

Findings are ordered by (kind, path, start, end).

| code | Meaning | Main threshold |
| --- | --- | --- |
| `OVERSIZED_INDIVISIBLE` | An oversized packet whose range cannot be split syntactically | — |
| `OVERSIZED_GAP_DISABLED` | An oversized range without syntax nodes mostly covered by `DISABLED_REGION` | `disabled_share` |
| `OVERSIZED_OTHER` | Any other oversized packet; never dropped | — |
| `DISABLED_CODE_VOLUME` | One per source: count, lines, share, inside/outside units, and the largest disabled range | — |
| `DISABLED_BLOCK_LARGE` | A disabled range with at least the threshold number of lines | `large_disabled_lines` |
| `TINY_SECTION` | A ready packet intersecting a unit whose target has at most the threshold number of lines | `tiny_lines` |
| `BAND_ONLY_SECTION` | A ready packet intersecting a unit whose target has no tokens | — |
| `ODD_INDENT_HEADING` | A heading whose indentation is not a multiple of the step | `indent_step` |
| `COMMENT_SEPARATED_FROM_CODE` | At a non-heading boundary, the previous packet ends with explanatory comment lines and the next packet starts with code | — |
| `CONTAINER_HEADER_SEPARATED` | A boundary between a container header (control, branch, block, handler) and its first child, leaving the header line in the previous packet | — |
| `MARKERS_AND_LONE_CR` | One per source: number of change-history lines (`markers.change`) and lone CRs | — |

Threshold defaults come from the profile's `report.*`, otherwise from generic defaults in the implementation. Kinds are kept in a registry, and thresholds are exposed automatically from the registry as `report` arguments. Kinds that depend on headings, annotations, or `lex` are not produced for sources without them. `report` returns exit code 0 even with findings (2 for invalid input and validation failures).
