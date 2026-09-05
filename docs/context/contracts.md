# データ契約と拡張

## 位置

全ての`start`／`end`は、デコード後の原文に対する**Unicode文字オフセット、0始まり、終端を含まない範囲**。バイト位置ではない。表示用の行番号は1始まり。CRLFは2文字として原文に保持する。日本語を含むPython ASTのバイト列位置は文字位置に変換する。

## Index schema 1

| 項目 | 内容 |
| --- | --- |
| `generator`, `runtime`, `adapters` | 生成器・実行環境・アダプターの版 |
| `sources` | `id`, `path`, `encoding`, `original_sha256`, `text_sha256`, `text`, `adapter` |
| `nodes` | `id`, `source_id`, `parent_id`, `kind`, `name`, `symbol`, `start`, `end`, `header_end`, 行番号, `confidence` |
| `edges` | `owner_id`, `source_id`, 根拠範囲, `kind`, `symbol`, `target_ids`, `resolution`, `evidence` |
| `diagnostics` | ソースID、範囲、コード、説明 |

各ソースに全文を覆うfileノードが1つある。兄弟ノードは重複しない。子は親の範囲に含まれる。子ノードの間の空白やコメントを木に登録する必要はなく、分割器が隙間を保存する。

辺の`kind`は初版では`call`、`reference`、`jump`。`resolution`は`candidate`（候補1つ）、`ambiguous`（候補複数）、`unresolved`。元コードの参照位置を保持する。名前の一致は意味解析や到達性の証明ではない。

## Pack schema 1

`policy`はアルゴリズム版、カウンターID、予算、予約枠、依存文脈数上限を持つ。

各packetは対象範囲、ID、状態、使用量、payloadハッシュ、`payload`文字列、`omitted_context`を持つ。

payload内の項目：

- `target`：解析対象の原文。全packetを通して欠落なく一度ずつ担当する。
- `enclosing_context`：対象が属する構造の原文ヘッダー。
- `relations`：対象内に根拠位置を持つ依存候補。同じkind・symbol・target_ids・resolutionの辺をまとめ、`occurrences`に全ての`[start, end]`を保持する。予算の都合で削らない。
- `exception_regions`：外側の例外領域への参照。適用の詳細は利用側で確認する。
- `dependency_context`：追加で添付した宣言やシグネチャ。呼出先全文が含まれるとは限らない。
- `diagnostics`：対象と交差する解析不能範囲。

状態は`ready`、`opaque`、`oversized`。サイズ超過と構造不明が重なる場合、状態は`oversized`になり、構造不明はpayloadのdiagnosticsに残る。

payloadハッシュは文字列そのもののSHA-256。整形し直すと変わる。予算もこの文字列全体に対して検証する。

## 言語アダプター

`code2map.context.Adapter` Protocolを満たすオブジェクトを`build_index(..., adapters=[...])`へ渡す。

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

構文対応後は、位置を持つchildrenと`Reference(kind, symbol, start, end)`を返す。スコープとして扱う共通kindは`file`, `package_body`, `package_spec`, `function`, `procedure`, `class`, `block`。その他のkindは範囲の階層を表す。

`header_end`は周辺文脈として必要なヘッダーの終端。本文全体を指定すると、分割後の文脈が巨大になるので注意する。認識不能な範囲は`opaque`とdiagnosticsの両方を返す。

外部アダプターは信頼されたPythonコードとして動く。code2mapはその実装をサンドボックス化しない。

## カウンター

`identity: str`と`count(text) -> int`を実装する。返す値は0以上の整数。カウンターの挙動は決定論的でなければならない。検査時も同じ実装を渡す。異なるカウンターIDでの検査は拒否する。
