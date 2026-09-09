# Examples

code2mapの使用例です。各言語のサンプルファイルと、その出力結果をバージョンごとのディレクトリに格納しています。

## Directory Structure

```
examples/
├── vX.Y.Z/                             # 最新バージョンの出力
│   ├── java/
│   │   ├── UserManagementService.java  # 入力ファイル
│   │   ├── output/                     # build の出力（INDEX.md, MAP.json, parts/）
│   │   └── context/                    # 共通エンジンの出力（index.json, pack.json, tree.txt, check.json）
│   ├── python/
│   │   ├── user_management_service.py  # 入力ファイル
│   │   ├── output/                     # build の出力（INDEX.md, MAP.json, parts/）
│   │   └── context/                    # 共通エンジンの出力（index.json, pack.json, tree.txt, check.json）
│   ├── plsql/
│   │   ├── accounting.sql              # 入力ファイル
│   │   └── context/                    # 共通エンジンの出力（build は PL/SQL 非対応）
│   └── csharp/
│       ├── UserManagementService.cs    # 入力ファイル（v0.5.0 から）
│       └── context/                    # 共通エンジンの出力（build は C# 非対応）
└── （旧バージョン）/                    # 参照用。context/ と plsql/ は共通エンジンを持つバージョンにのみある
```

## Usage

いずれもリポジトリルートから実行します。`EX` に最新バージョンのディレクトリを入れてください。

```bash
EX=docs/examples/v0.4.0
```

### build（Java・Python）

```bash
uv run code2map build $EX/java/UserManagementService.java --out $EX/java/output
uv run code2map build $EX/python/user_management_service.py --out $EX/python/output
```

### 共通エンジン（Java・Python・PL/SQL・C#）

`index` で索引を作り、`pack` で予算に応じた packet に分割し、`tree` で構造木、`check` で整合性検査の結果を保存します。索引に記録されるパスは入力ファイルからの相対パスなので、実行するディレクトリによって出力は変わりません。`build` は PL/SQL に対応していないため、PL/SQL は共通エンジンの出力だけを収録しています。

```bash
for lang in java python plsql csharp; do
  case $lang in
    java)   src=$EX/java/UserManagementService.java;   budget=6000 ;;
    python) src=$EX/python/user_management_service.py; budget=6000 ;;
    plsql)  src=$EX/plsql/accounting.sql;              budget=3000 ;;
    csharp) src=$EX/csharp/UserManagementService.cs;   budget=6000 ;;
  esac
  uv run code2map index $src --output $EX/$lang/context/index.json
  uv run code2map pack $EX/$lang/context/index.json --output $EX/$lang/context/pack.json --budget-bytes $budget --reserve-bytes 0
  uv run code2map tree $EX/$lang/context/index.json > $EX/$lang/context/tree.txt
  uv run code2map check $EX/$lang/context/index.json --pack $EX/$lang/context/pack.json > $EX/$lang/context/check.json
done
```

予算は、各サンプルが複数の `ready` な packet に分かれる値として選んでいます。既定の 16000 バイトでは、いずれも 1〜2 packet に収まります。

## 再生成についての補足

出力は入力が同じであれば常に同じ結果になります（静的解析のみで、LLM は使用していません）。出力ファイルに生成日時は含まれません。

そのため、バージョン間で出力が変わるのは解析ロジックに変更があった場合のみです。`build` の出力は、`parts/` の各ファイル冒頭にある `original:` 行（入力ファイルのパスを記録する行）を除いて比較できます。この行はディレクトリ名がバージョンごとに異なるため必ず差分になり、それ以外に差分が無ければ出力は変わっていません。`INDEX.md` と `MAP.json` は入力パスを含まないため、バイト単位で比較できます。

共通エンジンの `index.json` には実行環境として Python のバージョンが記録され、`index_sha256` と packet の ID はその値に依存します。収録した出力の生成環境は `index.json` の `runtime` を参照してください。別のバージョンの Python で再生成すると、構造や分割結果が同じでもハッシュと ID が変わります。詳細は [共通エンジンの設計](../context/architecture_ja.md) を参照してください。

旧バージョンの出力を再生成する場合は、対応する git tag を checkout した実装を使用してください。

## Sample Files

### Java: UserManagementService.java

ユーザー管理システムのサービスクラス。以下の機能を含みます：

- `UserManagementService`: メインサービスクラス
  - ユーザーの登録、更新、削除
  - ユーザーの検索（ID、年齢範囲、メールドメイン）
  - 入力バリデーション
- `User`: ユーザーエンティティ
- `UserAlreadyExistsException`: ユーザー重複例外
- `UserNotFoundException`: ユーザー未発見例外

### Python: user_management_service.py

Javaサンプルと同等の機能をPythonで実装したもの。以下の機能を含みます：

- `UserManagementService`: メインサービスクラス
  - ユーザーの登録、更新、削除
  - ユーザーの検索（ID、年齢範囲、メールドメイン）
  - 入力バリデーション
- `User`: ユーザーエンティティ（dataclass）
- `UserAlreadyExistsException`: ユーザー重複例外
- `UserNotFoundException`: ユーザー未発見例外

### PL/SQL: accounting.sql

共通エンジンの動作を示す小さな合成パッケージ（リポジトリ直下の `examples/accounting.sql` と同じ内容）。以下の要素を含みます：

- `ACCOUNTING` パッケージ仕様部と本体
  - `adjusted`: 金額に係数を掛けて返す関数
  - `calculate`: ループと IF 分岐で合計を求め、`INSERT` と `COMMIT` を行うプロシージャ。`EXCEPTION` 節で `ROLLBACK` して再送出
  - 初期化部でパッケージ変数 `g_total` を初期化

### 共通エンジンの出力（各言語の `context/`）

- `index.json`: 原文、構造木、字句上の依存候補、診断。実行環境（Python のバージョン）とアダプターの版を記録
- `pack.json`: 対象範囲・外側の宣言・依存候補・例外領域の参照を持つ packet。対象範囲を連結すると原文を重複なく復元できる
- `tree.txt`: `tree` コマンドが表示する構造木
- `check.json`: 索引と packet の整合性検査の結果
