# Examples

code2mapの使用例です。各言語のサンプルファイルと、その出力結果を格納しています。

## Directory Structure

```
examples/
├── v0.4.0/                             # 最新バージョンの出力
│   ├── java/
│   │   ├── UserManagementService.java  # 入力ファイル
│   │   └── output/                     # build の出力結果
│   │       ├── INDEX.md
│   │       ├── MAP.json
│   │       └── parts/
│   ├── python/
│   │   ├── user_management_service.py  # 入力ファイル
│   │   └── output/                     # build の出力結果
│   │       ├── INDEX.md
│   │       ├── MAP.json
│   │       └── parts/
│   └── plsql/
│       ├── accounting.sql              # 入力ファイル
│       └── output/                     # 共通エンジン（index / pack / tree / check）の出力結果
│           ├── index.json
│           ├── pack.json
│           ├── tree.txt
│           └── check.json
├── v0.3.0/                             # 旧バージョンの出力（参照用）
│   ├── java/
│   └── python/
├── v0.2.1/                             # 旧バージョンの出力（参照用）
│   ├── java/
│   └── python/
├── v0.2.0/                             # 旧バージョンの出力（参照用）
│   ├── java/
│   └── python/
└── v0.1.2/                             # 旧バージョンの出力（参照用）
    ├── java/
    └── python/
```

## Usage

### Java

```bash
# リポジトリルートから実行
uv run code2map build docs/examples/v0.4.0/java/UserManagementService.java --out docs/examples/v0.4.0/java/output
```

### Python

```bash
# リポジトリルートから実行
uv run code2map build docs/examples/v0.4.0/python/user_management_service.py --out docs/examples/v0.4.0/python/output
```

### PL/SQL（共通エンジン）

`build` は Java と Python のみ対応です。PL/SQL は 0.4.0 で追加した共通エンジン（`index` / `pack` / `check` / `tree` / `show`）で扱います。索引に記録されるパスは入力ファイルからの相対パス（ここでは `accounting.sql`）なので、実行するディレクトリによって出力は変わりません。

```bash
# リポジトリルートから実行
uv run code2map index docs/examples/v0.4.0/plsql/accounting.sql --output docs/examples/v0.4.0/plsql/output/index.json
uv run code2map pack docs/examples/v0.4.0/plsql/output/index.json --output docs/examples/v0.4.0/plsql/output/pack.json --budget-bytes 3000 --reserve-bytes 0
uv run code2map tree docs/examples/v0.4.0/plsql/output/index.json > docs/examples/v0.4.0/plsql/output/tree.txt
uv run code2map check docs/examples/v0.4.0/plsql/output/index.json --pack docs/examples/v0.4.0/plsql/output/pack.json > docs/examples/v0.4.0/plsql/output/check.json
```

予算 3000 バイトは、この 37 行のサンプルが 3 つの `ready` な packet に分かれる値として選んでいます（既定の 16000 バイトでは 1 packet に収まります）。

## 再生成についての補足

出力は入力が同じであれば常に同じ結果になります（静的解析のみで、LLM は使用していません）。出力ファイルに生成日時は含まれません。

そのため、バージョン間で出力が変わるのは解析ロジックに変更があった場合のみです。v0.2.1・v0.3.0・v0.4.0 の `build` 出力は、`parts/` の各ファイル冒頭にある `original:` 行（入力ファイルのパス）を除いて完全に一致します。`INDEX.md` と `MAP.json` はバイト単位で同一です。

共通エンジンの `index.json` には実行環境として Python のバージョンが記録され、`index_sha256` と packet の ID はその値に依存します。`v0.4.0/plsql/output` は Python 3.11 で生成しています。別のバージョンの Python で再生成すると、構造や分割結果が同じでもハッシュと ID が変わります。詳細は [共通エンジンの設計](../context/architecture_ja.md) を参照してください。

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
- `tree.txt` に構造木、`pack.json` に対象範囲・外側の宣言・依存候補を持つ packet、`check.json` に全範囲を重複なく覆っていることの検査結果が入ります
