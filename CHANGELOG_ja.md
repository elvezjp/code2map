[English](./CHANGELOG.md) | [日本語](./CHANGELOG_ja.md)

# 変更履歴

このプロジェクトに対する注目すべき変更をこのファイルに記録します。

このファイルの形式は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に基づいており、
このプロジェクトは [セマンティックバージョニング](https://semver.org/lang/ja/) に準拠しています。

## [未リリース]

## [0.3.0] - 2026-08-09

推移的な開発依存パッケージ `cryptography` の 2 件のアドバイザリに対応し、あわせて `versions/` ディレクトリを廃止して git tag によるバージョン管理へ移行しました（[#17](https://github.com/elvezjp/code2map/issues/17)）。実装および各コマンドの出力に変更はありません。

### セキュリティ

- **`cryptography` の下限を `>= 50.0.0` に引き上げ**、[GHSA-g6cj-pr64-35w5](https://github.com/pyca/cryptography/security/advisories/GHSA-g6cj-pr64-35w5) / [CVE-2026-69247](https://nvd.nist.gov/vuln/detail/CVE-2026-69247)（High）に対応。PKCS#7 `EnvelopedData` の復号処理が失敗内容を区別可能な形で返しており、コンテンツ暗号化鍵に対する Bleichenbacher オラクルとなる問題です。影響範囲は `>= 44.0.0, < 50.0.0`
  - Dependabot アラート #13 を解消
  - `uv.lock` を再生成（`cryptography` 49.0.0 → 50.0.0）
- `[未リリース]` に記録していた分: `cryptography` の下限を `>= 48.0.1` に引き上げ、[GHSA-537c-gmf6-5ccf](https://github.com/pyca/cryptography/security/advisories/GHSA-537c-gmf6-5ccf)（`cryptography` の wheel `< 48.0.1` に脆弱な OpenSSL が同梱されている問題）に対応
  - `pyproject.toml` に `[tool.uv]` の `constraint-dependencies` を追加
  - 上記 `>= 50.0.0` の制約に包含されるため、現在は 1 つの制約で両方のアドバイザリをカバーしています
- **いずれのアドバイザリもランタイムには影響しません**: `cryptography` は Linux 上で `twine` → `keyring` → `SecretStorage` 経由でのみ導入され、これらはすべて開発依存です。code2map 自体の依存は `tree-sitter` と `tree-sitter-java` のみで、PKCS#7 の API は使用していません
  - アラートは開発環境全体を解決する `uv.lock` に対して報告されたものです。code2map を利用するだけのユーザーに `cryptography` は導入されません

### 変更

- **バージョン管理を git tag へ移行**（[#17](https://github.com/elvezjp/code2map/issues/17)）: 旧バージョンのスナップショットを保持していた `versions/` ディレクトリを削除し、リポジトリのルートで最新コードのみを管理する方針に変更
  - 旧バージョン（v0.1.1〜v0.2.0）のスナップショットは `v0.2.1` タグの `versions/` 配下に保存されています。同タグは旧構成のアーカイブ参照点であり、削除・付け替えを行わないでください
  - `versions/` 配下の lockfile に起因していた Dependabot アラートの重複通知を解消（同一のアドバイザリがアーカイブされた manifest の数だけ報告されていました）
  - v0.1.1〜v0.2.0 のタグは遡って作成していません。`pyproject.toml` に記録されたバージョンが履歴上で前後しており（例: `61b5887` の `0.2.0` が `03448d7` の `0.1.2` より前）、各リリースに対応するコミットを確実に特定できないためです
  - README（日英）に「バージョン管理」セクションを追加し、SECURITY（日英）の Dependabot アラート運用方針を更新
- `pyproject.toml` の sdist 除外リストから `/versions` を削除

### 追加

- **v0.3.0 の出力サンプル**を `docs/examples/v0.3.0/`（Java・Python）に追加。本バージョンで再生成したものです
  - v0.2.1 のサンプルとは、`parts/` 各ファイルの `original:` 行（入力ファイルのパスを記録する行）以外は同一です。`INDEX.md` と `MAP.json` はバイト単位で一致しており、本リリースで出力が変わらないことを裏付けています
  - `docs/examples/README.md` に、出力が決定的である（静的解析のみで LLM を使用せず、出力に生成日時を含まない）ことの注記を追加

## [0.2.1] - 2026-05-12

### 変更

- **Python 最低バージョンを 3.9 から 3.11 に引き上げ**（[#14](https://github.com/elvezjp/code2map/issues/14)）
  - `pyproject.toml`: `requires-python = ">=3.11"`、classifiers から `Python :: 3.9` / `Python :: 3.10` を削除
  - CI matrix を `["3.9", "3.12"]` → `["3.11", "3.13"]` に更新
  - README / CONTRIBUTING / spec.md の要件を Python 3.11+ に更新

### 追加

- **PyPI 公開向けパッケージメタデータ**（[#12](https://github.com/elvezjp/code2map/issues/12)）
  - `[project]` 拡充: `authors` に連絡先、`keywords`、`classifiers` 追加（`Development Status :: 3 - Alpha`、`Intended Audience :: Developers`、`Topic :: Software Development :: *`、`Python :: 3 :: Only`）
  - `[project.urls]` に `Homepage` / `Documentation` / `Changelog` / `Issues` を追加
  - `[project.optional-dependencies].dev` に `build` / `twine` を追加
  - `[tool.hatch.build.targets.wheel]` と `[tool.hatch.build.targets.sdist]` を設定し、`versions/`、`docs/`、`main.py`、`.github/` を配布物から除外

### 修正

- `code2map.__version__` を `pyproject.toml` の version に追従（`"0.2.0"` のままだったのを修正）

### セキュリティ

- **Dependabot アラート [#2](https://github.com/elvezjp/code2map/security/dependabot/2) を解消**: pytest が 9.0.3 に解決されるようになった（CVE-2025-71176, Medium 6.8 を修正）。従来は `requires-python = ">=3.9"` のため、pytest 9.x が Python 3.10+ を要求する関係で脆弱な pytest 8.4.2 に固定されていた。

### 備考

- v0.2.0 のスナップショットを `versions/v0.2.0/` に保存

## [0.2.0] - 2026-03-12

### 変更

- **JavaパーサーをTree-sitterに置き換え**: `javalang` を `tree-sitter` + `tree-sitter-java` に全面置き換え（[#9](https://github.com/elvezjp/code2map/issues/9)）
  - Java 8+構文（ラムダ式、メソッドリファレンス `Type[]::new` 等）を正常にパース可能
  - 構文エラー時もエラー箇所の行番号を含む警告を返す（部分的なパース結果は返却）
  - record、sealed class、switch式など将来の新構文にも対応可能

### 追加

- **テスト**: Java 8+構文の正常パース・エラー時の警告返却テストを追加

### 変更（依存関係）

```diff
- javalang>=0.13.0
+ tree-sitter>=0.21.0
+ tree-sitter-java>=0.21.0
```

- v0.1.3 のスナップショットを `versions/v0.1.3/` に保存

## [0.1.3] - 2026-03-12

### 修正

- **Javaパースエラーメッセージ改善**: Java 8+構文を含むファイルのパースが失敗した際、エラーメッセージが空になっていた問題を修正（[#9](https://github.com/elvezjp/code2map/issues/9)）
  - `JavaSyntaxError` の `description` 属性と `at` 属性を使用し、エラーの原因と発生箇所を出力するように変更
  - 修正前: `"Java parse error: "`（空）
  - 修正後: `"Java parse error: Expected '.' (at Keyword "new" line N, position M)"`

### 追加

- **テスト**: Javaパースエラーメッセージに関するテストケースを3件追加
- **テストフィクスチャ**: Java 8+構文（メソッドリファレンス `Type[]::new`）を含むJavaファイルを追加

### 変更

- v0.1.2 のスナップショットを `versions/v0.1.2/` に保存

## [0.1.2] - 2026-02-25

### 修正

- **ファイル名サニタイズ**: parts/ のファイル名からWindows不可文字（`< > : " / \ | ? *`）を除去するようになりました（[#5](https://github.com/elvezjp/code2map/issues/5)）
  - Javaコンストラクタ `<init>` のファイル名が `User_<init>.java` → `User_init.java` に変更
  - Windows環境で `git clone` が失敗する問題を解消
  - サニタイズにより同名になった場合も既存のハッシュサフィックス機構で衝突を回避

### 追加

- **テスト**: ファイル名サニタイズに関するテストケースを3件追加

### 変更

- サンプル出力ファイル（`docs/examples/java/output/`）を再生成
- 仕様書（`spec.md`）にファイル名サニタイズの仕様を追記
- v0.1.1 のスナップショットを `versions/v0.1.1/` に保存

## [0.1.1] - 2026-02-06

### 追加

- **シンボルID機能**: 各シンボルに一意の識別子を付与
  - `--id-prefix`: シンボルIDのプレフィックスを指定できるようになりました（デフォルト: `CD`）
  - INDEX.md: シンボル名の前に `[CD1]` 形式でIDを表示
  - MAP.json: `id` フィールドを先頭に追加
  - parts/: ヘッダに `id: CD1` 行を追加

- **テスト**: ID機能に関するテストを追加

### 変更

- Symbol モデルに `id` フィールドを追加

## [0.1.0] - 2026-01-27

初回リリース。Python・Java両言語に対応したMVP版。

### 追加

- **CLIコマンド**: `code2map build` コマンドを実装
  - `--out`: 出力ディレクトリを指定できるようになりました
  - `--lang`: 言語を明示的に指定できるようになりました（省略時は拡張子から自動検出）
  - `--verbose`: 詳細なログを出力できるようになりました
  - `--dry-run`: 実際にファイルを生成せず、計画のみ表示できるようになりました

- **Pythonパーサー**: `ast`モジュールを使用した解析機能
  - クラス、メソッド、関数の抽出に対応
  - Docstringの抽出に対応
  - 呼び出し関係の推定に対応
  - Import情報の収集に対応

- **Javaパーサー**: `javalang`ライブラリを使用した解析機能
  - クラス、メソッド、フィールドの抽出に対応
  - Javadocの抽出に対応
  - 呼び出し関係の推定に対応
  - ネストクラス、コンストラクタ、オーバーロードに対応

- **INDEX.md生成**: クラス/メソッド/関数の一覧と役割を記載したMarkdown索引
  - 呼び出し関係（Calls）の表示
  - 副作用（Side Effects）の検出・記載
  - 警告（`[WARNING]`）の埋め込み

- **parts/生成**: ソースコードをクラス/メソッド単位で分割
  - メタデータヘッダの付与
  - 言語別コメントプレフィックス対応
  - 名前衝突回避のためのハッシュサフィックス

- **MAP.json生成**: 機械可読な対応表（JSON形式）
  - シンボル情報の完全なマッピング
  - SHA-256チェックサムの計算

- **テスト**: ユニットテスト、e2eテスト、エッジケーステストを整備

- **CI/CD**: GitHub Actionsによる自動テスト（Python 3.9〜3.12対応）

### 既知の制限事項

このバージョンには以下の制限があります：

- 単一ファイルのみ対応（ディレクトリ単位の解析は未対応）
- 静的解析のみ対応（動的ディスパッチ、リフレクションは考慮しない）
- クラス/メソッド単位の分割のみ（処理フェーズ単位の分割は未対応）
- 対応言語はJavaとPythonのみ

## リンク

- [リポジトリ](https://github.com/elvezjp/code2map)
- [Issueトラッカー](https://github.com/elvezjp/code2map/issues)

[0.3.0]: https://github.com/elvezjp/code2map/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/elvezjp/code2map/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/elvezjp/code2map/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/elvezjp/code2map/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/elvezjp/code2map/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/elvezjp/code2map/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/elvezjp/code2map/releases/tag/v0.1.0
