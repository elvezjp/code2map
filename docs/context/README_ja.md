# 共通エンジン — 0.4.0開発版

[English](README.md) | [日本語](README_ja.md)

code2mapは、**原文全体の索引化**と**対象範囲に文脈を添える入力の組立て**を分けています。レビュー、文書化、移行、LLMツールから、特定のモデル提供元に依存せず利用できます。ライセンスはリポジトリ共通のMITです。

## 0.3.0からの移行

| 用途 | コマンド | 出力 |
| --- | --- | --- |
| 従来のクラス・関数抽出 | `build file.py --out output` | 従来どおりの`INDEX.md`、`MAP.json`、`parts/` |
| 原文全体の構造索引 | `index file-or-directory --output index.json` | schema 1の原文スナップショット、階層、字句上の依存候補 |
| 文脈付き分割 | `pack index.json --output pack.json` | schema 1の対象範囲と補足文脈を持つpacket群 |

`build`は引き続きPythonとJavaに対応します。クラスとメソッドの断片は意図的に重複します。共通エンジンはPython・Java・PL/SQLに対応し、全packetの対象範囲を通して索引内の各原文を一度ずつ網羅します。ソースの書き換えや、コンパイル可能なモジュールの生成は行いません。従来の`MAP.json`は索引スナップショットとは異なります。`pack`を使うには元ソースを`index`で索引化してください。

## CLI

[ルートREADMEの手順](../../README_ja.md)で開発ブランチを取得し、リポジトリのルートで実行します。`NODE_ID`は`tree`が各行の末尾に表示するIDに置き換えてください。

```bash
uv sync --locked --all-extras
uv run code2map index examples --output output/index.json
uv run code2map tree output/index.json --depth 3
uv run code2map pack output/index.json --output output/pack.json \
  --budget-bytes 16000 --reserve-bytes 2000 --dependency-limit 8
uv run code2map check output/index.json --pack output/pack.json
uv run code2map show output/index.json NODE_ID
```

`index`は単一ファイル、またはディレクトリ内で再帰的に選択した対応ファイルを受け付けます。拡張子は`.py`、`.java`、`.sql`、`.pks`、`.pkb`、`.pls`、`.plsql`です。隠しパスと`node_modules`、`__pycache__`、`build`、`dist`は除外し、未対応ファイルは読み飛ばします。既定は厳密なUTF-8デコードです。旧資産には`--encoding cp932`等を指定します。索引にはデコード後のソース全文が含まれます。

### 引数と既定値

| コマンド | 引数・オプション | 内容 |
| --- | --- | --- |
| `index` | `input`、`--output PATH` | 入力と出力は必須。出力名は`.json` |
| `index` | `--encoding` | 既定`utf-8`。`utf-8-sig`、`cp932`、`shift_jis`、`euc_jp`も選択可能 |
| `pack` | `index`、`--output PATH` | 索引と出力は必須。出力名は`.json` |
| `pack` | `--budget-bytes` | 既定`16000`、正の整数 |
| `pack` | `--reserve-bytes` | 既定`0`、0以上かつ予算未満 |
| `pack` | `--dependency-limit` | 既定`8`、0以上。任意の補足抜粋の件数上限 |
| `check` | `index`、`--pack PATH` | 索引は必須。packも検査するときに`--pack`を指定 |
| `tree` | `index`、`--depth` | 索引は必須。深さは既定`3`、0以上。fileルートが深さ0 |
| `show` | `index`、`node_id` | 両方必須。出典情報と指定ノードの原文を表示 |

共通オプションは`--help`、トップレベルの`--version`です。出力先の親ディレクトリは自動作成されます。既存の出力JSONは置換されます。`index`による入力ソースの上書きと`pack`による入力索引の上書きは拒否します。

### 終了コードとpacketの扱い

共通エンジンのコマンドは、成功が0、不正入力や検証失敗が2、索引化の診断あり、またはpackに`opaque`／`oversized`が含まれる場合が3です。終了コード3でも診断付きの成果物を書き出します。`check`は成果物にこれらの状態が含まれていても、内部の整合性を満たせば0を返します。**すべてのpacketがreadyという意味ではありません。** 従来の`build`の終了コードは[仕様書](../../spec.md)を参照してください。

`packets[i].payload`は、利用側がソースデータとして渡せるJSON文字列です。CLIはこの文字列全体を**UTF-8バイト数で測ります。トークン数ではありません。** `reserve`は指示文、チャットの付加情報、出力に確保する枠として予算から差し引かれます。適切な予約枠は利用側で決めてください。`omitted_context`は予算や件数のために添付できなかった抜粋を記録し、関係のIDはpayload内にも残ります。送信前に状態と省略内容を確認してください。

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
        # 利用側で、この文脈が調査に十分か判断する。
```

モデル固有のカウンターはAPIから渡せます。

```python
class ModelTokens:
    def __init__(self, tokenizer, identity):
        self.tokenizer = tokenizer
        # 実装、語彙の版、オプションを識別できる値を指定する。
        self.identity = identity

    def count(self, text):
        return len(self.tokenizer.encode(text, add_special_tokens=False))

# counter = ModelTokens(your_tokenizer, "your-pinned-tokenizer-revision")
# packed = pack_index(index, budget=8192, reserve=2048, counter=counter)
# validate_pack(index, packed, counter=counter)
```

信頼された独自言語アダプターを`build_index(..., adapters=[...])`へ渡すと、組込みアダプターを置き換えられます。Protocolとデータクラスは`code2map.context`から公開しています：`Adapter`、`BudgetCounter`、`Node`、`Parsed`、`Reference`、`UTF8Bytes`。ノード種別と位置の定義は[データ契約](contracts_ja.md)を参照してください。

## 保証の範囲と制約

- スナップショットはデコード後の原文、CRLF、コメント、空白を保持します。位置は0始まりのUnicode文字数、終端を含まない範囲です。表示用の行番号は1始まりです。元のエンコード済みバイト列との違いは[データ契約](contracts_ja.md)で説明しています。
- 相対パス、ソースのバイト列、文字コード、Python・実行環境・アダプターの版、分割設定、カウンターの挙動を固定すると出力は決定論的です。時刻や絶対パスを含みません。原文を変えるとIDも変わり、編集をまたぐ同一性は保証しません。
- 対象範囲は各原文を一度ずつ網羅し、補足文脈は重複を許します。検査では網羅性、原文一致、必須ヘッダーと関係、payloadのハッシュ、予算、依存文脈の省略記録、状態を確認します。ハッシュは整合性検査であり、署名ではありません。
- 予算はシリアライズ済みpayloadに適用します。分割不能な文、長いヘッダー、解析不能範囲は超過することがあります。原文を保持し、黙って切り捨てません。
- `candidate`と`ambiguous`は字句上の根拠であり、実行時の結合やデータフローを証明しません。修飾付きの外部呼出しは未解決になり得ます。`ready`はサイズと報告された診断に基づく状態であり、完全なプログラム理解を示しません。
- PL/SQLスキャナーはOracleの完全な文法やコンパイラではありません。未対応部分は失敗を検知した際に診断付きで保持します。構造の受理はOracleでの妥当性を証明しません。
- JavaはTree-sitterを使い、本体と文法の版を記録します。構文エラー時はファイル全体を`opaque`にします。式、匿名クラス、ラムダの内部を再帰分割しません。do-whileは末尾条件を失わないよう分割不能とします。型推論、import先、継承、動的ディスパッチは解決しません。
- Pythonは実行中のインタープリターのASTを使い、importを実行しません。動的な言語機能や完全な`global`／`nonlocal`の結合解析は未実装です。

詳細は[設計](architecture_ja.md)、[データ契約](contracts_ja.md)、[言語別の制約](limitations_ja.md)を参照してください。

## 開発

```bash
uv run pytest
uv run ruff check .
uv build
```

テストは、従来の出力動作、原文全体の網羅性、Unicode／CRLF、分岐・例外の文脈、曖昧な依存候補、opaque／oversized、独自アダプターとカウンター、保存済み成果物の検証、公開CLIを対象にしています。

確認した環境と互換性比較は[検証記録](validation_ja.md)を参照してください。
