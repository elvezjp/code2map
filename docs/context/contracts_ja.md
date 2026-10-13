# データ契約と拡張

[English](contracts.md) | [日本語](contracts_ja.md)

## 位置

全ての`start`／`end`は、デコード後の原文に対する**Unicode文字オフセット、0始まり、終端を含まない範囲**。バイト位置ではない。表示用の行番号は1始まり。CRLFは2文字として原文に保持する。Python ASTとJava CSTのバイト位置は文字位置に変換する。

## Index schema 1

| 項目 | 内容 |
| --- | --- |
| `schema_version` | `1`。パッケージの版とは独立 |
| `generator`, `runtime`, `adapters` | 生成器・実行環境・アダプターの版 |
| `sources` | `id`, `path`, `encoding`, `original_sha256`, `text_sha256`, `text`, `adapter` |
| `nodes` | `id`, `source_id`, `parent_id`, `kind`, `name`, `symbol`, `start`, `end`, `header_end`, `start_line`, `end_line`, `confidence` |
| `edges` | `id`, `owner_id`, `source_id`, `start`, `end`, `kind`, `symbol`, `target_ids`, `resolution`, `evidence` |
| `diagnostics` | `source_id`, `start`, `end`, `code`, `message` |

各ソースに全文を覆うfileノードが1つある。兄弟ノードは重複しない。子は親の範囲に含まれる。子ノードの間の空白やコメントを木に登録する必要はなく、分割器が隙間を保存する。分割器は子ノードの境界で範囲を分けるとき、境界を行の先頭・末尾に揃える（字下げの後で始まる子や行末コメントの前で終わる子でも、隣の範囲に行の断片を残さない。同じ行を2つの子が共有する場合は先の子がその行を持つ）。

`original_sha256`は元のバイト列、`text_sha256`はデコード後の文字列をUTF-8にした値のハッシュです。たとえば`utf-8-sig`ではBOMを除去した文字列を保存します。復元対象はデコード後の原文であり、元のエンコード済みバイト列とは限りません。

辺の`kind`は`call`、`reference`、`jump`。`resolution`は`candidate`（候補1つ）、`ambiguous`（候補複数）、`unresolved`。元コードの参照位置を保持する。未解決のcall／jumpは残し、候補のない通常のreferenceはグラフから省略する。名前の一致は意味解析や到達性の証明ではない。

## Pack schema 1

最上位は`schema_version`、`index_sha256`、`policy`、`packets`、`summary`を持つ。`policy`はアルゴリズム版、カウンターID、予算、予約枠、依存文脈数上限を持つ。schemaの版はパッケージの版とは独立。

各packetは`id`、`source_id`、`start`、`end`、`status`、`budget_used`、`payload_sha256`、`payload`文字列、`omitted_context`を持つ。

payload内の項目：

- `index_sha256`：固定した入力索引の識別情報。
- `instruction`：解析対象の範囲と解釈上の制限。
- `target`：解析対象の原文。全packetを通して欠落なく一度ずつ担当する。
- `enclosing_context`：対象が属する構造の原文ヘッダー。
- `relations`：対象内に根拠位置を持つ依存候補。同じkind・symbol・target_ids・resolutionの辺をまとめ、`occurrences`に全ての`[start, end]`を保持する。予算の都合で削らない。
- `exception_regions`：外側の例外領域への参照。適用の詳細は利用側で確認する。
- `dependency_context`：追加で添付した宣言やシグネチャ。呼出先全文が含まれるとは限らない。
- `diagnostics`：対象と交差する解析不能範囲。

状態は`ready`、`opaque`、`oversized`。サイズ超過と構造不明が重なる場合、状態は`oversized`になり、構造不明はpayloadのdiagnosticsに残る。`ready`は対象に交差する診断がなく、予算に収まることを意味し、完全な意味理解を示さない。

`omitted_context`はpayloadの外側にあり、`node_id`と`reason`（`budget`または`dependency_limit`）を記録する。LLMへの送信前にrelationsと併せて確認する。`summary`はpacket総数と状態別の件数を持つ。

payloadハッシュは文字列そのもののSHA-256。整形し直すと変わる。予算もこの文字列全体に対して検証する。`index_sha256`は索引の正規化JSON（キー順ソート、2スペース字下げ、Unicodeをエスケープせず末尾LF付き）のハッシュ。

## 言語アダプター

`code2map.context.Adapter` Protocolを満たすオブジェクトを`build_index(..., adapters=[...])`へ渡す。この一覧は組込みアダプターを置き換える。

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

構文対応後は、位置を持つchildrenと`Reference(kind, symbol, start, end)`を返す。スコープとして扱う共通kindは`file`, `package_body`, `package_spec`, `namespace`, `function`, `procedure`, `class`, `block`。`namespace`は配下の名前の修飾にも使う。その他のkind（`control`・`branch`・`handler`・`label`・`preproc`など）は範囲の階層だけを表す。

`header_end`は周辺文脈として必要なヘッダーの終端。本文全体を指定すると、分割後の文脈が巨大になるので注意する。認識不能な範囲は`opaque`とdiagnosticsの両方を返す。

外部アダプターは信頼されたPythonコードとして動く。code2mapはその実装をサンドボックス化しない。

## カウンター

`identity: str`と`count(text) -> int`を実装する。返す値は0以上の整数。カウンターの挙動は決定論的でなければならない。検査時も同じ実装を渡す。IDには実装、語彙の版、設定を含める。異なるカウンターIDでの検査は拒否する。既定の`UTF8Bytes`はUTF-8バイト数を測り、トークン数の推定ではない。

## 次の版で追加する契約（実装前）

この章は、次の版で追加する契約の仕様である。**まだ実装されていない。** 上の Index schema 1・Pack schema 1 は現行の版の契約であり、実装されるまでは上の記述が有効である。

次の版では、書き手がコメントで書いた節の見出し、解析はできているが注意が要る範囲、分割結果の診断を扱えるようにする。いずれも**言語や書き方に依存しない仕組み**として実装し、特定の書き方に固有の値（区切り線の形、変更履歴の書式、無効化の規約など）は、プロファイル（後述）で外から与える。プロファイルを与えなければ、見出しと書き方に依存する注記は出ない。

### プロファイル

プロファイルは、ソースの書き方の規則を与える TOML ファイルである。`index --profile PATH` で渡す。

- `index` はプロファイルを検査し、正規化した内容とその SHA-256 を索引の `profile` に保存する。`pack`・`report`・`check` は索引に保存したプロファイルを使い、別のプロファイルを受け取らない（索引と分割の規則がずれないようにするため）。
- 未知の項目、型の違い、コンパイルできない正規表現は、索引を書く前に終了コード2で止める。
- 実装はどの書き方の値も既定値として持たない。プロファイルを与えなければ、`headings` は空になり、書き方に依存する注記（`DISABLED_REGION`・`HEADING_FALLBACK`）は出ない。

| 項目 | 内容 |
| --- | --- |
| `profile.id` | 利用者が付けるプロファイルの名前（索引に記録する） |
| `headings.separator` | 区切り線とみなす行コメントの正規表現（例：同じ記号が一定数以上続く行） |
| `headings.title_skip` | 見出し本文を探すときに読み飛ばす行の正規表現（例：変更履歴の行、装飾だけの行） |
| `headings.title_exclude` | 見出しにしない本文の正規表現 |
| `headings.indent_from` | 見出しの字下げをどの行から取るか（`title`＝本文行／`separator`＝区切り線） |
| `headings.tab_indent` | 字下げにタブを含む見出しの扱い（`fallback`＝索引に載せず注記する） |
| `markers.change` | 変更履歴の行（例：改修の開始・終了を示すコメント行）の正規表現。分割の境界を上げるときの止め位置と、診断の件数に使う |
| `annotations.disabled_region` | 無効化されたコードとみなす範囲の規則（例：行頭から始まるブロックコメント）。与えたときだけ注記する |
| `report.*` | 診断の閾値の既定値（コマンドの引数で上書きできる） |

### 言語アダプターの追加の能力

コメント見出しの検出には、コメントとリテラルの範囲が要る。アダプターは、任意の能力として `lex(text)` を持てる。`lex` は、行コメント・ブロックコメント・文字列リテラルの範囲を返す。`lex` を持たないアダプターのソースでは、見出しと書き方に依存する注記を作らない。分割や再計算の処理は、アダプターの名前ではなく、この能力の有無で分岐する。

最初は PL/SQL アダプターが `lex` を持つ。

### Index schema 2

Index schema 1 に次を加える。

| 項目 | 内容 |
| --- | --- |
| `schema_version` | `2` |
| `profile` | `null`、または `{id, sha256, content}`（正規化したプロファイル） |
| `headings` | `id`, `source_id`, `owner_id`, `parent_heading_id`, `start`, `end`, `title_start`, `title_end`, `section_end`, `start_line`, `title_line`, `indent`, `style`, `title` |

見出しは、書き手がコメントで書いた手順の区切りであり、構文木の外に置く。nodes と単位の範囲は、見出しのために変えない。

- **検出**：プロファイルの `headings.separator` に当たる区切り線の直後の、コメントだけの本文行を見出しとする。`headings.title_skip` に当たる行は読み飛ばし、区切り線・コード行・空行で打ち切る。ブロックコメントや文字列の中に描かれた区切り線は見出しにしない。
- **所属**：`owner_id` は帯を含む最内側の関数・手続き（スコープとして扱う kind）。どの単位にも含まれない見出しは索引に載せない。
- **範囲**：`start`／`end` は帯（上の区切り線の行頭から、本文行と、対になる下の区切り線があればその末尾まで）。上の区切り線を直前の見出しと共有する見出しは、帯を本文行から始める。同じ owner の帯は重ならない。`title_start`／`title_end` は本文行（改行を除く）、`title` はコメント記号と前後の空白を除いた文言。
- **階層**：`parent_heading_id` は、同じ owner の中で直前まで有効な、より浅い字下げの見出し。最上位は `null`。`section_end` は、次の同じ深さか浅い見出しの `start`、無ければ owner の終端。階層は書き手の目次であり、制御フローの証明ではない。
- **ID**：`identity("heading", source_id, owner_id, start, end)`。同じ文言でも、位置が違えば別の ID になる。
- **検査**：固定した原文と保存したプロファイルから見出しを再計算し、保存済みの headings と比べる。

schema 1 の索引は、次の版の `check`・`pack`・`report` では明示的に拒否する（黙って補完しない）。`index` から作り直す。

### Pack schema 2

Pack schema 1 に次を加える。

- **`policy.algorithm`**：`structural-greedy-v1`（現行の方式。既定）と `structural-heading-v1`（見出し優先の分割と、切れ目の巻き上げ。[設計](architecture_ja.md)）のどちらか。`pack --algorithm` で選ぶ。既定を変えないので、既存の利用者の出力は変わらない。
- **`policy.profile_sha256`**：索引に保存したプロファイルのハッシュ（無ければ `null`）。
- **packet ID**：`identity("packet-v2", index_sha256, canonical(policy), source_id, start, end)`。policy の項目を1つでも変えると、すべての packet ID が変わる。過去の packet ID を新しい実行に流用しない。
- **`enclosing_context` の見出し**：対象と適用区間 `[start, section_end)` が重なる見出しとその祖先を、`role: section-heading` の抜粋として加える（`heading_id`・`owner_id`・`parent_heading_id` と、他の抜粋と同じ位置の項目を持つ）。見出しの抜粋は target と重なることがあり、予算に数える。
- **`annotations`**：対象と交差する「解析はできているが注意が要る」範囲。diagnostics とは別で、packet の状態には影響しない。各要素は `id`、`source_id`、`kind`、`start`、`end`、`start_line`、`end_line`、`message` を持つ。区間は原文上の区間のままで、packet の範囲に切り詰めない。交差は半開区間で判定する。注記は payload の一部として予算に数える。

| kind | 意味 | 条件 |
| --- | --- | --- |
| `SOURCE_LONE_CR` | 直後が LF でない CR。行番号は LF 基準なので、この文字は行を進めない | 全言語・常に |
| `DISABLED_REGION` | 無効化されたコードとみなす範囲。原文は target に残り、ノード・辺・診断は生じない。プロファイルの規約に基づく注記であり、その範囲が本当に使われていないことを保証しない | `annotations.disabled_region` を与えたとき。字句解析に失敗したソースには付けない |
| `HEADING_FALLBACK` | 分割の境界に使えない見出しの帯（字下げにタブを含む、文・宣言・構文ヘッダーの内側にある、など） | `structural-heading-v1` のとき |

- **検査**：同じ索引・policy・カウンターから分割計画を再計算し、packet の範囲の列と一致することを確かめる。

schema 1 の pack は、次の版の `check`・`report` では明示的に拒否する。`pack` から作り直す。

### Report schema 1（分割結果の診断）

`report INDEX --pack PACK --output DIR` は、pack の派生物として `report.json`（機械が読む正本）と `report.md`（人が読む形）を書く。index・pack・packet ID は変えない。閾値は、何を列挙するかを選ぶだけである。同じ index・pack・閾値からは同じ `report.json` が出る（実行日時や絶対パスを含まない）。`report.md` は原文の本文を含まない（行番号と見出しの文言は含む）。`report.md` の文言は `--lang en|ja` で選ぶ（既定 `en`）。

最上位は `schema_version`（`1`）、`generator`、`index_sha256`、`pack_sha256`、`policy`、`pack_summary`、`thresholds`、`attribution_defaults`、`counts`、`counts_by_attribution`、`findings`。

各 finding は次を持つ。

- `code`
- `attribution_default`：原因の初期値。`source`（原文の書き方）／`rule`（分割の規則）／`budget`（予算）／`mixed`／`unknown`。種類ごとの初期値であり、機械が確定するものではない。
- `attribution_override`：人が原因を上書きする欄。生成時は `null`。
- `source_id`・`path`・`start`・`end`・`start_line`・`end_line`・`lines`・`bytes`
- `unit`：所属する関数・手続き。単位の外や、複数にまたがるときは `null`。
- `reason`：固定の文言と数値。
- `measures`：種類ごとの数値。
- `refs`：`packet_ids`・`heading_ids`・`annotation_ids`・`node_ids`。

findings は（種類、path、start、end）の順に並べる。

| code | 内容 | 主な閾値 |
| --- | --- | --- |
| `OVERSIZED_INDIVISIBLE` | oversized の packet で、範囲が構文上切れない | — |
| `OVERSIZED_GAP_DISABLED` | 構文ノードを含まない oversized の範囲の大半が `DISABLED_REGION` で覆われる | `disabled_share` |
| `OVERSIZED_OTHER` | 上のどちらでもない oversized。落とさない | — |
| `DISABLED_CODE_VOLUME` | ソースごとに1件。無効化範囲の数・行数・全体比・単位内外の内訳・最大の範囲 | — |
| `DISABLED_BLOCK_LARGE` | 行数が閾値以上の無効化範囲 | `large_disabled_lines` |
| `TINY_SECTION` | 単位に交差する ready な packet で、target の行数が閾値以下 | `tiny_lines` |
| `BAND_ONLY_SECTION` | 単位に交差する ready な packet で、target にトークンが無い | — |
| `ODD_INDENT_HEADING` | 見出しの字下げが刻みの倍数でない | `indent_step` |
| `COMMENT_SEPARATED_FROM_CODE` | 見出し以外の境界で、直前の packet が説明コメントの行で終わり、次の packet がコードで始まる | — |
| `CONTAINER_HEADER_SEPARATED` | 容器（制御・分岐・ブロック・ハンドラー）のヘッダーと最初の子の間に境界があり、ヘッダー行が前の packet に残る | — |
| `MARKERS_AND_LONE_CR` | ソースごとに1件。変更履歴の行（`markers.change`）の行数と、単独 CR の件数 | — |

閾値の既定値は、プロファイルの `report.*`、無ければ実装の汎用の既定値とする。種類は登録表で管理し、閾値は登録表から `report` の引数として自動で出す。見出し・注記・`lex` に依る種類は、それらが無いソースでは出ない。`report` は、finding があっても終了コード0を返す（不正な入力と検査の失敗は2）。
