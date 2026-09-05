# `build`コマンド仕様書

[English](spec_en.md) | [日本語](spec.md)

この文書は0.4.0開発版に継承した`build`の仕様です。新しい`index`／`pack`／`check`／`tree`／`show`とPython APIは[共通エンジンガイド](docs/context/README_ja.md)および[データ契約](docs/context/contracts_ja.md)を参照してください。旧`MAP.json`は`pack`の入力には使えません。

## 1. 目的と範囲

単一のPython／Javaファイルからクラス・メソッド・関数を抽出し、索引、断片、行番号対応表を生成します。大規模コードの構造確認、対象を絞ったレビュー、元ソースへの参照を支援します。

生成断片はコンパイル・実行用ではありません。import補完、実行時の依存解決、動的解析、フォーマッタ／Linterの代替、正しさを保証した設計書の自動生成は対象外です。callsとside effectsは静的な候補・ヒューリスティックです。

クラス断片はメソッド本文も含み、メソッド断片と重複します。トップレベルのimportや定数等は抽出対象外になり得ます。`build`は原文全体の網羅性や入力予算を保証しません。それらには`index`／`pack`を使用してください。

## 2. 入力と環境

| 項目 | 仕様 |
| --- | --- |
| 入力 | 単一ソースファイル |
| 言語 | Python `.py`、Java `.java`。`--lang`で明示指定可能 |
| 文字コード | UTF-8を前提。デコード不能なバイトはU+FFFDに置換し警告 |
| 改行 | 行分割して処理。断片本文はLFで結合するため元の改行バイト列は保持しない |
| Python | 3.11以上 |
| 依存 | `tree-sitter`、`tree-sitter-java` |
| OS | Windows／macOS／Linux向け。確認範囲は[検証記録](docs/context/validation_ja.md)参照 |

数千行規模のレビューを想定していますが、全入力に対する実行時間やメモリ上限は保証しません。ソースをメモリに読み込み、構文木を構築します。`build`は単一ファイル用で、ディレクトリ索引化は共通エンジンに実装しています。

## 3. CLI

```text
code2map build input_file [--out DIR] [--lang {java,python}]
               [--id-prefix PREFIX] [--verbose] [--dry-run]
```

| 引数・オプション | 必須 | 既定値 | 内容 |
| --- | --- | --- | --- |
| `input_file` | 必須 | — | 解析するファイル |
| `--out` | 任意 | `./code2map-out` | 出力ディレクトリ |
| `--lang` | 任意 | 拡張子から判定 | `java`または`python` |
| `--id-prefix` | 任意 | `CD` | シンボルIDの接頭辞 |
| `--verbose` | 任意 | false | 詳細ログ |
| `--dry-run` | 任意 | false | 書き込まずシンボルと出力予定を表示 |

`--lang`未指定で未知の拡張子の場合はエラーです。`--help`はヘルプを表示します。トップレベルの`code2map --version`は版を表示します。

| 終了コード | 意味 |
| --- | --- |
| 0 | 警告なしで成功 |
| 1 | 入力ファイル不在、言語判定不可等の致命的エラー |
| 2 | パーサー警告ありで生成またはdry-run完了。CLI引数の不備もargparseにより2となる |

構文エラーは通常、警告付きの結果として扱います。Pythonでパースに失敗するとシンボルは空、Javaでは抽出可能なシンボルを返します。パース失敗を一律に終了コード1とは扱いません。

出力先の親ディレクトリを作成し、今回生成する同名ファイルを上書きします。他のファイルや古い断片を自動削除しないため、厳密に今回分だけが必要なら新しい出力ディレクトリを使用してください。予期しないI/OエラーはPython例外として終了する場合があります。

## 4. 出力

### 4.1 `INDEX.md`

先頭は`# Index: <ファイル名>`。警告は`<!-- [WARNING] ... -->`として記録します。存在する種別について`Classes`、`Methods`、`Functions`の節を生成します。

各行はID、表示名、開始・終了行、断片の相対パスを持ちます。メソッド表示名は`ClassName#methodName`です。メソッド／関数には、情報がある場合のみ次の項目を追加します。クラスの行にはこれらの補足項目を出力しません。

| 項目 | 内容 |
| --- | --- |
| `role` | Docstring／Javadoc由来の最初の行を取り、最初のピリオドまでに短縮 |
| `calls` | 構文木から抽出した呼出名の一覧 |
| `side effects` | 対象本文のキーワード検出による副作用候補 |

断片への参照は`-> parts/...`というテキストで出力します。

### 4.2 `parts/`

| 種別 | ファイル名 |
| --- | --- |
| クラス | `<ClassName>.class.<ext>` |
| メソッド | `<Parent>_<methodName>.<ext>` |
| 関数 | `<functionName>.<ext>` |

ネストクラスはパーサーが渡すクラス名を使い、常に`Outer_Inner`へ展開するわけではありません。修飾名と親情報は内部のSymbolに保持します。ファイル名の`< > : " / \ | ? *`を除去します。例：Javaコンストラクター`<init>`は`User_init.java`になります。論理名やヘッダー表示名の`User#<init>`は変えません。

同一の候補名が既に使用済みなら、シグネチャ、または`表示名_開始行`のSHA-256先頭4文字を`__abcd`として付加します。最初の同名シンボルには接尾辞を付けません。短いハッシュなので、あらゆる入力での衝突回避を保証するものではありません。

ヘッダーはPythonでは`#`、Javaでは`//`のコメントで、次を記録します。

- `code2map fragment (non-buildable)`
- `id`：パーサーの返す順に接頭辞＋1始まりの連番（既定`CD1`等）
- `original`：元ファイルのパス
- `lines`：元ファイルの開始行–終了行（1始まり、終端を含む）
- `symbol`：表示名
- `notes`：存在する場合、import由来の参照名と呼出名

ヘッダー直後に改行を1つ置いて抽出本文を続け、最後に改行を付けます。空行を別途挿入するわけではありません。

### 4.3 `MAP.json`

CLIではIDを付与したJSON配列を出力します。配列順はパーサーのシンボル順です。

| フィールド | 型 | 内容 |
| --- | --- | --- |
| `id` | string | 接頭辞＋連番。ジェネレーターをIDなしで直接呼ぶ場合は省略 |
| `symbol` | string | シンボル表示名 |
| `type` | string | `class`、`method`、`function` |
| `original_file` | string | 元ファイルのベース名 |
| `original_start_line` | integer | 1始まりの開始行 |
| `original_end_line` | integer | 終端を含む終了行 |
| `part_file` | string | `parts/`から始まる相対パス |
| `checksum` | string | 以下の本文に対するSHA-256、小文字16進64文字 |

チェックサムの対象は**抽出本文だけ**です。追加したメタデータヘッダーと末尾の改行を含みません。元ソースを`splitlines()`し、対象の行を`"\n".join(...)`した文字列をUTF-8でエンコードして計算します。生成された断片ファイル全体のハッシュとは異なります。

```python
import hashlib
from pathlib import Path

lines = Path("examples/pricing.py").read_text(encoding="utf-8", errors="replace").splitlines()
start_line, end_line = 1, 3  # 実際のMAP.jsonに記録された範囲へ置き換える
fragment = "\n".join(lines[start_line - 1:end_line])
checksum = hashlib.sha256(fragment.encode("utf-8")).hexdigest()
```

## 5. 処理と言語対応

処理順は、入力確認、言語判定、パーサー選択、シンボルと警告の取得、ID付与、断片生成、INDEX生成、MAP生成です。dry-runでは書き込みの代わりにシンボルと生成予定を表示します。

パーサーは名前、種別、行範囲、親、修飾名、役割、呼出名、import由来の依存名を持つSymbolを返します。内部の詳細は`code2map/models/symbol.py`で定義しています。

| 要素 | Python AST | Java Tree-sitter CST |
| --- | --- | --- |
| クラス・ネストクラス | 抽出 | 抽出 |
| メソッド | 抽出 | 抽出 |
| トップレベル関数 | 抽出。asyncも対応 | 該当なし |
| ネスト関数 | 親に含め、個別断片にしない | 該当なし |
| コンストラクター | 通常のメソッドとして扱う | `<init>`として抽出 |
| interface／enum／record／annotation型 | 該当なし | クラス種別で抽出 |
| デコレーター／アノテーション | Pythonデコレーター行は断片範囲に含めない | 詳細な意味解析はしない |
| フィールド | 独立したシンボルとして抽出しない | 独立したシンボルとして抽出しない |
| ラムダ・メソッド参照等 | ASTが受理する構文を扱う | 文法が受理するJava 8+構文を扱う |

Pythonは`ast.Call`、Javaは`method_invocation`から呼出名を得ます。JavaのJavadocは直前のCSTコメントから取得します。Javaの行範囲はCSTの位置から決め、パースエラー時は行・列付きの警告と抽出可能な結果を返します。型推論、ジェネリクスの完全な結合、間接呼出先、リフレクション、動的ディスパッチは解決しません。

## 6. 副作用と診断

副作用は本文を小文字化し、固定の部分文字列を検索して分類します。下表は例であり、完全な規則は`code2map/generators/index_generator.py`を参照してください。

| 出力カテゴリ | 検出文字列の例 |
| --- | --- |
| `file io` | `open(`、`filewriter`、`outputstream`、`write(`、`path` |
| `stdout` | `print(`、`system.out`、`stderr` |
| `logging` | `logging.`、`logger.`、`log.` |
| `network` | `http`、`socket`、`request`、`client` |
| `db` | `jdbc`、`select `、`execute(`、`save`、`commit` |
| `exceptions` | `throw new`、`raise ` |

誤検出や見逃しがあり得ます。実行時の副作用や到達性を証明しません。ルールの設定ファイルによる変更は未実装です。

警告はINDEXと標準エラーに出し、MAPには含めません。`--verbose`がなくても警告は表示します。空のシンボルリストでもINDEXと空配列のMAPを生成します。エンコード不正時の置換と警告は、厳密なデコードを行う共通エンジンとは異なります。

## 7. 拡張方針

従来パーサーの拡張は`BaseParser.parse(file_path)`からシンボルと警告を返す方式です。共通エンジンの言語追加は別の`Adapter`契約で行います。両者を混同しないでください。

0.4.0では複数ファイルの索引化と構造に沿った予算付き分割を共通エンジンに追加しました。今後の優先事項は[対応範囲と残課題](docs/context/limitations_ja.md)にまとめています。設定ファイル、差分解析、追加言語、呼出グラフ表示、索引自動生成のCIテンプレート、Web UI、IDE連携は、実装済み機能とは区別した拡張候補です。

既存のINDEX／MAP／partsの出力契約を保ち、言語ごとの実装を分離し、新しい動作を明示的に選べる設計を維持します。
