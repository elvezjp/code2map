# code2map

[English](./README.md) | [日本語](./README_ja.md)

[![Elvez](https://img.shields.io/badge/Elvez-Product-3F61A7?style=flat-square)](https://elvez.co.jp/)
[![IXV Ecosystem](https://img.shields.io/badge/IXV-Ecosystem-3F61A7?style=flat-square)](https://elvez.co.jp/ixv/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Stars](https://img.shields.io/github/stars/elvezjp/code2map?style=social)](https://github.com/elvezjp/code2map/stargazers)

ソースコードの構造を索引化し、AI解析・レビュー向けに文脈付きの入力を組み立てるPythonライブラリ／CLIです。従来のシンボル抽出も利用できます。

![Input/Output Example](docs/assets/example.png)

## 文脈付き分割（0.4.0 開発版）

開発ブランチ`codex/20260905-context-partitioning`の0.4.0で、原文全体を先に索引化し、予算に応じて文脈付きの入力を組み立てる共通エンジンを追加しました。PL/SQL・Python・Java、およびこれらが混在するディレクトリに対応します。既存の`build`コマンドと出力形式も継続して利用できます。

[セットアップ](#セットアップ)後、リポジトリのルートで実行します。

```bash
uv run code2map index examples --output output/index.json
uv run code2map tree output/index.json --depth 3
uv run code2map pack output/index.json --output output/pack.json --budget-bytes 16000
uv run code2map check output/index.json --pack output/pack.json
```

各packetは対象原文、外側の条件・宣言、依存候補、例外領域の参照を持ちます。対象範囲を連結すると全原文を重複・欠落なく復元できます。補足文脈は対象とは別に保持します。入力ソースの実行、LLMやDBへの接続は行いません。

CLIの予算は**payload全文のUTF-8バイト数**です。モデルのトークン数ではありません。Python APIではモデル固有のカウンターへ差し替えられます。分割不能な巨大範囲や解析不能範囲は状態として明示します。`ready`は予算内という意味で、完全な意味解析を保証しません。

[共通エンジンの利用ガイド](docs/context/README_ja.md)、[設計](docs/context/architecture_ja.md)、[データ契約](docs/context/contracts_ja.md)、[対応範囲](docs/context/limitations_ja.md)を参照してください。

## ユースケース

- **AIコードレビュー**: 大規模ファイルを構造に沿って分割し、対象を絞ったレビューを支援
- **コード構造の可視化**: クラス・メソッドの一覧と依存関係を索引として出力
- **行番号マッピング**: AIの指摘箇所を元ファイルの行番号に確実に対応付け
- **ドキュメント生成の補助**: コード構造を把握した上での設計書作成を支援

## 開発の背景

本ツールは、日本の開発現場でAIを活かすためのAI開発エコシステム **IXV（イクシブ）** の開発過程で生まれた小さな実用品です。

IXVでは、開発方法論とOSSを提供することで、AI活用を現場に根付かせる取り組みを進めており、本リポジトリでは、その一部を切り出して公開しています。

## `build`の特徴

- **意味的な分割**: クラス・メソッド・関数単位でコードを分割（ビルド用ではなくレビュー用）
- **Markdown索引生成**: 役割説明・呼び出し関係・副作用を含むINDEX.mdを自動生成
- **行番号対応表**: 分割片と元ファイルの対応をMAP.json（機械可読）で提供
- **Python・Java対応**: AST解析（Python）および tree-sitter CST解析（Java）による構文上のシンボル抽出（Java 8+構文対応）
- **ドライラン機能**: 実際の出力前に生成計画を確認可能

## ドキュメント

- [共通エンジンの利用ガイド](docs/context/README_ja.md) - 移行、CLI全オプション、終了コード、Python API
- [設計](docs/context/architecture_ja.md) - 決定論と文脈の組立て
- [データ契約](docs/context/contracts_ja.md) - schemaと拡張インターフェース
- [対応範囲・制約](docs/context/limitations_ja.md) - 実装済み機能と残課題
- [検証記録](docs/context/validation_ja.md) - テストと確認環境

- [CHANGELOG_ja.md](CHANGELOG_ja.md) - バージョン履歴
- [CONTRIBUTING_ja.md](CONTRIBUTING_ja.md) - コントリビューション方法
- [SECURITY_ja.md](SECURITY_ja.md) - セキュリティポリシー
- [spec.md](spec.md) - 従来の`build`仕様書
- [examples/](examples/) - 共通エンジン用のPL/SQL・Python・Javaサンプル
- [docs/examples/](docs/examples/) - 旧リリースの`build`入出力例

## セットアップ

### 必要環境

- Python 3.11以上
- [uv](https://docs.astral.sh/uv/)（推奨パッケージマネージャー）

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/elvezjp/code2map.git
cd code2map

# 未リリースの0.4.0開発ブランチを選択
git switch codex/20260905-context-partitioning

# uvで依存関係をインストール（仮想環境も自動作成）
uv sync --locked --all-extras

# 動作確認
uv run code2map --version
uv run code2map --help
```

## `build`の使い方

### 基本的な実行

```bash
# Pythonファイルを解析
uv run code2map build your_code.py --out ./output

# Javaファイルを解析
uv run code2map build YourCode.java --out ./output
```

### 出力の確認

```bash
# 索引を確認
cat output/INDEX.md

# 分割されたコード片を確認
ls output/parts/

# 行番号対応表を確認
cat output/MAP.json
```

### ドライラン（プレビュー）

```bash
# ファイルを生成せずに計画を確認
uv run code2map build your_code.py --dry-run
```

## `build`の主要オプション

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--out <DIR>` | `./code2map-out` | 出力ディレクトリ |
| `--lang {java,python}` | 自動検出 | 言語の明示指定 |
| `--id-prefix <PREFIX>` | `CD` | シンボルIDのプレフィックス（CD1, CD2, ...） |
| `--verbose` | false | 詳細ログを出力 |
| `--dry-run` | false | ファイル生成せずプレビューのみ |

詳細は `uv run code2map build --help` を参照してください。

## `build`の出力例

### INDEX.md

以下は書式を示す模式例です。実際の出力例は[旧リリースのサンプル](docs/examples/)を参照してください。

```markdown
# Index: user_management.py

## Classes
- [CD1] UserManager (L10–L150) → parts/UserManager.class.py

## Methods
- [CD2] UserManager#create_user (L45–L80) → parts/UserManager_create_user.py
  - role: 新規ユーザーを作成する
  - calls: validate_email, hash_password
  - side effects: DB操作
```

### MAP.json

```json
[
  {
    "id": "CD1",
    "symbol": "UserManager",
    "type": "class",
    "original_file": "user_management.py",
    "original_start_line": 10,
    "original_end_line": 150,
    "part_file": "parts/UserManager.class.py",
    "checksum": "a1b2c3d4..."
  }
]
```

## ディレクトリ構成

```text
code2map/
├── code2map/              # メインパッケージ
│   ├── cli.py             # CLIエントリーポイント
│   ├── context/           # 原文索引、文脈付き分割、検証
│   │   └── adapters/      # PL/SQL・Python・Javaアダプター
│   ├── generators/        # 出力生成モジュール
│   │   ├── index_generator.py   # INDEX.md生成
│   │   ├── map_generator.py     # MAP.json生成
│   │   └── parts_generator.py   # parts/生成
│   ├── models/            # データモデル
│   │   └── symbol.py      # シンボル情報クラス
│   ├── parsers/           # 言語パーサー
│   │   ├── base_parser.py     # 基底クラス
│   │   ├── java_parser.py     # Javaパーサー
│   │   └── python_parser.py   # Pythonパーサー
│   └── utils/             # ユーティリティ
│       ├── file_utils.py  # ファイル操作
│       └── logger.py      # ログ設定
├── examples/              # 共通エンジン用の合成サンプル
├── tests/                 # テストコード
│   └── fixtures/          # テストフィクスチャ
├── docs/                  # ドキュメント
│   ├── context/           # 共通エンジン文書（日英）
│   ├── assets/            # 画像等のアセット
│   ├── examples/          # 使用例とサンプル入出力
│   └── tests/             # テスト指示書・結果
├── CHANGELOG.md           # 変更履歴
├── CONTRIBUTING.md        # コントリビューションガイド
├── README.md              # 英語版README
├── README_ja.md           # 本ファイル（日本語版）
├── SECURITY.md            # セキュリティポリシー
├── spec.md                # build仕様書（日本語）
├── spec_en.md             # build仕様書（英語）
└── pyproject.toml         # プロジェクト設定
```

## バージョン管理

リポジトリのルートでは最新のコードのみを保持し、バージョン管理は git tag で行います。

- `main` ブランチには次バージョンの変更を [CHANGELOG_ja.md](CHANGELOG_ja.md) の `## [未リリース]` 見出しの下に蓄積します
- リリース時に `pyproject.toml` のバージョンを確認し、見出しの日付を確定したうえで `vX.Y.Z` タグを作成します

### 旧バージョンを利用する場合

旧バージョン（v0.1.1〜v0.2.0）は、以前は `versions/` ディレクトリ配下にスナップショットとして保持していました。この構成は `v0.2.1` タグに保存されています。

```bash
git checkout v0.2.1
# 旧バージョンは versions/ 配下にあります
```

**注意**: `v0.2.1` タグは旧構成のアーカイブ参照点のため、削除・付け替えを行わないでください。

## 制約

- `build`はPython・Javaの単一ファイルからシンボルを抽出します。断片は重複し、入力サイズを制限しません。
- `index`はPL/SQL・Python・Javaのファイル／ディレクトリに対応し、`pack`は原文の構造に沿って分割します。分割不能な範囲は予算を超える場合があります。
- 呼出しや変数参照は静的な候補です。完全なデータフローや実行時の結合は解決しません。

[build仕様書](spec.md)と[共通エンジンの制約](docs/context/limitations_ja.md)を参照してください。

## セキュリティ

セキュリティに関する詳細は [SECURITY_ja.md](SECURITY_ja.md) を参照してください。

- 信頼できないソースからのファイル処理には注意してください
- 出力ファイルには元のソースコードが含まれます

## コントリビューション

コントリビューションを歓迎します。詳細は [CONTRIBUTING_ja.md](CONTRIBUTING_ja.md) を参照してください。

- バグ報告・機能提案: [Issues](https://github.com/elvezjp/code2map/issues)
- プルリクエスト: ブランチ命名規則 `{ユーザー名}/{日付}-{内容}`

## 変更履歴

詳細は [CHANGELOG_ja.md](CHANGELOG_ja.md) を参照してください。

## ライセンス

MIT License - 詳細は [LICENSE](LICENSE) を参照してください。

## 問い合わせ先

- **Issues**: [GitHub Issues](https://github.com/elvezjp/code2map/issues)
- **メール**: info@elvez.co.jp
- **会社**: [株式会社エルブズ](https://elvez.co.jp/)
