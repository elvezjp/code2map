# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-26

### Added

#### CLI
- `code2map build` コマンド実装
- `--out` オプション（出力ディレクトリ指定）
- `--lang` オプション（言語明示指定）
- `--verbose` オプション（詳細ログ出力）
- `--dry-run` オプション（ドライラン）
- 言語自動検出（拡張子ベース）
- 終了コード正規化（0=成功、1=エラー、2=警告あり）

#### Parsers
- **Python パーサー** (`ast` モジュールベース)
  - クラス、メソッド、関数の抽出
  - Docstring 抽出
  - 呼び出し関係の推定
  - Import 情報の収集
  
- **Java パーサー** (`javalang` ベース)
  - クラス、メソッド、フィールドの抽出
  - Javadoc 抽出
  - 呼び出し関係の推定
  - ネストクラス対応
  - コンストラクタ対応
  - オーバーロード検出（ハッシュベース一意化）

#### Generators
- **INDEX.md 生成**
  - クラス/メソッド/関数の一覧表示
  - 役割（Role）情報の記載
  - 呼び出し関係（Calls）の表示
  - 副作用（Side Effects）の検出・記載
  - 警告（`[WARNING]`）の埋め込み

- **parts/ 生成**
  - ソースコード分割（クラス/メソッド単位）
  - メタデータヘッダ付与
  - 言語別コメントプレフィックス対応
  - ハッシュサフィックスによる名前衝突回避

- **MAP.json 生成**
  - 機械可読な対応表（JSON形式）
  - SHA-256 チェックサム計算
  - シンボル情報の完全なマッピング

#### Utilities
- ファイル操作（UTF-8 読み書き）
- ハッシュ計算（SHA-256）
- ログ設定（標準 `logging` ライブラリ）
- 行抽出・スライス

#### Testing
- ユニットテスト（Python/Java パーサー）
- 生成ロジックテスト
- e2e テスト（CLI 実行テスト）
- エッジケーステスト（空ファイル、構文エラー、大規模ファイル）

#### CI/CD
- GitHub Actions ワークフロー
  - Python 3.9, 3.10, 3.11, 3.12 での自動テスト
  - ruff lint チェック
  - mypy 型チェック
  - pytest + カバレッジレポート生成
  - Codecov へのアップロード

#### Documentation
- README.md（インストール・使い方・ワークフロー）
- Spec.md（詳細仕様）
- Plan.md（実装計画）
- CHANGELOG.md（本ファイル）

### Known Limitations
- **入力スコープ**: 単一ファイルのみ対応。ディレクトリ単位の解析は未対応。
- **依存解析**: 静的解析のみ。動的ディスパッチ、リフレクションは考慮しない。
- **分割粒度**: クラス/メソッド単位のみ。処理フェーズ単位の分割は未対応。
- **言語**: Java と Python のみサポート。

### Not Implemented
- 複数ファイル/ディレクトリ解析
- 設定ファイルのカスタマイズ
- GitHub PR への自動コメント
- Web UI
- IDE プラグイン
- C++/Go/Rust/TypeScript サポート

---

## Roadmap

### Phase 5 (v0.2.0)
- [ ] ディレクトリ/複数ファイル対応
- [ ] 設定ファイル（YAML/TOML）で分割粒度カスタマイズ
- [ ] Tree-sitter への移行による精度向上

### Phase 6 (v0.3.0)
- [ ] C++/Go/Rust/TypeScript サポート
- [ ] 世代比較・差分表示機能
- [ ] 変更影響度の可視化

### Phase 7 (v1.0.0)
- [ ] Web UI（ブラウザベース INDEX.md ビューア）
- [ ] GitHub Actions Integration
- [ ] IDE プラグイン（VSCode, IntelliJ）
