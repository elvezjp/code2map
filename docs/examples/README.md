# Examples

code2mapの使用例です。各言語のサンプルファイルと、その出力結果を格納しています。

## Directory Structure

```
examples/
├── v0.3.0/                             # 最新バージョンの出力
│   ├── java/
│   │   ├── UserManagementService.java  # 入力ファイル
│   │   └── output/                     # 出力結果
│   │       ├── INDEX.md
│   │       ├── MAP.json
│   │       └── parts/
│   └── python/
│       ├── user_management_service.py  # 入力ファイル
│       └── output/                     # 出力結果
│           ├── INDEX.md
│           ├── MAP.json
│           └── parts/
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
uv run code2map build docs/examples/v0.3.0/java/UserManagementService.java --out docs/examples/v0.3.0/java/output
```

### Python

```bash
# リポジトリルートから実行
uv run code2map build docs/examples/v0.3.0/python/user_management_service.py --out docs/examples/v0.3.0/python/output
```

## 再生成についての補足

出力は入力が同じであれば常に同じ結果になります（静的解析のみで、LLM は使用していません）。出力ファイルに生成日時は含まれません。

そのため、バージョン間で出力が変わるのは解析ロジックに変更があった場合のみです。v0.2.1 と v0.3.0 の出力は、`parts/` の各ファイル冒頭にある `original:` 行（入力ファイルのパス）を除いて完全に一致します。`INDEX.md` と `MAP.json` はバイト単位で同一です。

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
