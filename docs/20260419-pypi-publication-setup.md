# 20260419 PyPI 公開構成整備 修正計画書

関連 Issue: [#12 PyPIへのパッケージ公開](https://github.com/elvezjp/code2map/issues/12)
対象バージョン: `code2map` v0.2.0 (最新)

## 1. 目的

`code2map` を PyPI に公開し、他の Python プロジェクトから `pip install code2map` で
利用できるようにする。そのために、現在のリポジトリ構成・パッケージングメタデータを
PyPI 公開に耐える状態へ整える。

## 2. 現状の整理

- ビルドバックエンド: `hatchling` (`pyproject.toml` 設定済み)
- 最新バージョン: `0.2.0` (`pyproject.toml` / `code2map/__init__.py`)
- パッケージ本体: ルート直下の `code2map/` パッケージ
  - `code2map.cli:main` を CLI エントリーポイントとして提供済み
- ランタイム依存: `tree-sitter>=0.21.0`, `tree-sitter-java>=0.21.0`
- 開発依存 (optional): `pytest`, `pytest-cov`, `ruff`, `mypy`
- Python 対応バージョン: `>=3.9`
- ライセンス: MIT (`LICENSE` あり)
- README: `README.md` (英語、`README_ja.md` も並存)
- `versions/v0.1.1 .. v0.1.3/` に旧バージョンのスナップショットが同梱
- ルートに `main.py` (ローカル実行用の薄いラッパ) が存在
- `tests/` ディレクトリは配布物には不要

## 3. PyPI 公開のための仕様

### 3.1 パッケージメタデータ (`[project]`)

- `name`: `code2map`
- `version`: `0.2.0` (Issue 指示により今回バージョンは据え置き)
- `description`: 現行のまま
- `readme`: `README.md` (英語を PyPI の説明として採用)
- `requires-python`: `>=3.9`
- `license`: `MIT` (SPDX 表記 `license = { text = "MIT" }` を維持)
- `authors`: `code2map developers <info@elvez.co.jp>`
- `keywords`: `code`, `map`, `ast`, `tree-sitter`, `code-review`, `llm`, `static-analysis`
- `classifiers`:
  - `Development Status :: 3 - Alpha`
  - `Intended Audience :: Developers`
  - `License :: OSI Approved :: MIT License`
  - `Operating System :: OS Independent`
  - `Programming Language :: Python :: 3`
  - `Programming Language :: Python :: 3 :: Only`
  - `Programming Language :: Python :: 3.9`
  - `Programming Language :: Python :: 3.10`
  - `Programming Language :: Python :: 3.11`
  - `Programming Language :: Python :: 3.12`
  - `Topic :: Software Development`
  - `Topic :: Software Development :: Code Generators`
  - `Topic :: Software Development :: Libraries :: Python Modules`

### 3.2 URL (`[project.urls]`)

- `Homepage` = `https://github.com/elvezjp/code2map`
- `Repository` = `https://github.com/elvezjp/code2map`
- `Documentation` = `https://github.com/elvezjp/code2map#readme`
- `Changelog` = `https://github.com/elvezjp/code2map/blob/main/CHANGELOG.md`
- `Issues` = `https://github.com/elvezjp/code2map/issues`

### 3.3 エントリーポイント

- `code2map = "code2map.cli:main"` (既存を維持)

### 3.4 ビルド構成 (`hatchling`)

- `wheel` には `code2map/` パッケージのみ含める
  - `[tool.hatch.build.targets.wheel] packages = ["code2map"]`
- `sdist` には以下のみ含める
  - `code2map/`, `tests/`, `README.md`, `README_ja.md`, `LICENSE`, `CHANGELOG.md`,
    `CHANGELOG_ja.md`, `CONTRIBUTING.md`, `CONTRIBUTING_ja.md`, `SECURITY.md`,
    `SECURITY_ja.md`, `spec.md`, `pyproject.toml`
- 配布物から除外するもの
  - `versions/` (旧バージョンのスナップショット。配布サイズ肥大化と依存関係上のノイズを避けるため除外)
  - `docs/`, `docs/assets/`, `docs/examples/` (リポジトリ内の参考資料。PyPI 配布物としては不要)
  - `main.py` (ローカル実行用、CLI エントリーポイントがあるので配布物として不要)
  - `.github/`, テスト/IDE 関連 (`.pytest_cache`, `.vscode`, `.claude` など)

### 3.5 ライセンス・法的表記

- `LICENSE` を sdist / wheel の両方に含める (hatchling デフォルトで対応)

### 3.6 インポート動作の確認

- `import code2map` が成功する
- `from code2map import __version__` が `"0.2.0"` を返す
- `python -m code2map` は現状 CLI として定義されていないため、対象外
  (今回は `code2map` コンソールスクリプト経由を公式手段とする)

## 4. 公開までの全体計画

### フェーズ A: リポジトリ整備 (本 PR のスコープ)

1. `pyproject.toml` の拡充 (urls, classifiers, keywords, build 設定, authors)
2. `hatchling` の wheel / sdist 対象ファイル設定
3. `uv.lock` の再生成
4. ローカルで `python -m build` を実行しビルド成果物を確認
5. `pytest` で既存テストがすべて通ることを確認
6. 計画書 (本ファイル) に実装記録を残す

### フェーズ B: 公開準備 (管理者が実施、今回の PR 対象外)

7. PyPI / TestPyPI アカウント作成、API トークン取得
8. `twine check dist/*` で成果物の健全性確認
9. TestPyPI にアップロードし `pip install -i https://test.pypi.org/simple/ code2map` で検証
10. 本番 PyPI に公開

### フェーズ C: 継続運用 (任意・本 PR 対象外)

11. GitHub Actions による Trusted Publisher 設定 (OIDC ベースの自動公開)
12. リリースフロー (タグ → CI → PyPI 公開) の整備
13. `CHANGELOG.md` のリリースノート連携

## 5. 本 PR で実施するタスク詳細

### T1. `pyproject.toml` 更新

- `[project]` に `keywords`, `authors` (連絡先付き) を追加・拡充
- `classifiers` を 3.1 節の一覧に更新
- `[project.urls]` を 3.2 節の内容に拡充
- `[tool.hatch.build.targets.wheel]` を追加し `packages = ["code2map"]` を明示
- `[tool.hatch.build.targets.sdist]` を追加し include/exclude を設定
- ビルドバックエンドは `hatchling` のまま据え置き

### T2. `uv.lock` 再生成

- 既存の `uv.lock` を削除し、`uv lock` を実行して最新化

### T3. ビルド確認

- `uv run python -m build` で `dist/code2map-0.2.0-py3-none-any.whl` と
  `dist/code2map-0.2.0.tar.gz` が生成されることを確認
- 生成された成果物に `versions/` が含まれていないこと、
  `code2map/` パッケージ本体が含まれていることを確認

### T4. 既存テスト実行

- `uv run pytest` を実行し、全件 PASS することを確認
- 旧バージョン (`versions/` 配下) のテストは対象外

### T5. 実装記録の追記

- 本計画書 §7 に実装結果を追記

## 6. 検証 / 受け入れ項目 (管理者用)

管理者は以下を確認することで、本 PR の受け入れ可否を判断できる。

- [ ] `pyproject.toml` の `[project.urls]` に Homepage / Repository / Documentation /
      Changelog / Issues が登録されている
- [ ] `pyproject.toml` の `classifiers` に Development Status / Topic / Python
      バージョン行が含まれている
- [ ] `pyproject.toml` の `keywords` にパッケージの特徴を表すキーワードが含まれている
- [ ] `[tool.hatch.build.targets.wheel]` で `code2map` パッケージのみが wheel に
      梱包されている
- [ ] `[tool.hatch.build.targets.sdist]` で `versions/`, `main.py`, `docs/` などが
      除外され、必要なファイルのみ含まれる
- [ ] `uv.lock` がコミット済みで、最新の依存関係を反映している
- [ ] `python -m build` により `dist/code2map-0.2.0-py3-none-any.whl` と
      `dist/code2map-0.2.0.tar.gz` がエラーなく生成できる
- [ ] 生成した wheel / sdist を解凍し、`code2map/` と必要なメタファイルのみが入って
      いる (旧バージョンが含まれていない)
- [ ] `pytest` が全件 PASS する
- [ ] `twine check dist/*` が PASSED を返す (管理者側で実施)
- [ ] TestPyPI へアップロードし、別環境で `pip install code2map` して
      `code2map --help` が動作する (管理者側で実施)

## 7. 実装記録

### 実施内容 (2026-04-19)

- `pyproject.toml` を更新
  - `[project]`: `authors` に連絡先を追加 (`info@elvez.co.jp`)、`keywords` を追加、
    `classifiers` を拡充 (Development Status / Intended Audience / Topic 系を追加)
  - `[project.urls]`: `Homepage`, `Documentation`, `Changelog`, `Issues` を追加
  - `[project.optional-dependencies].dev` に `build`, `twine` を追加
  - `[tool.hatch.build.targets.wheel]` で `packages = ["code2map"]` を明示
  - `[tool.hatch.build.targets.sdist]` で include/exclude を定義し、
    `versions/`, `docs/`, `main.py`, `.github/` などを除外
- `uv.lock` を削除し `uv lock` → `uv sync --all-extras` で再生成 / 同期
- `uv run python -m build` でビルド確認
  - `dist/code2map-0.2.0-py3-none-any.whl` (16,200 bytes)
  - `dist/code2map-0.2.0.tar.gz` (41,650 bytes)
- 生成物を解凍して中身を検証
  - wheel: `code2map/` (cli, generators, models, parsers, utils) + `dist-info` のみ。
    `versions/`, `main.py`, `docs/` が含まれないことを確認
  - sdist: `code2map/`, `tests/`, ルートのライセンス・ドキュメント類のみ。
    `versions/`, `main.py`, `docs/` が含まれないことを確認
- `uv run twine check dist/*` が両成果物で `PASSED`
- 別の空 venv で `pip install dist/code2map-0.2.0-py3-none-any.whl` を実行し、
  `code2map --help` の CLI 動作および `import code2map; code2map.__version__ == "0.2.0"` を確認
- `uv run pytest` を実行、30 件すべて PASS

## 8. 残タスク (本 PR スコープ外)

- PyPI / TestPyPI アカウント作成および API トークン取得 (管理者)
- TestPyPI での公開検証 (管理者)
- 本番 PyPI への公開 (管理者)
- (任意) GitHub Actions による Trusted Publisher / 自動リリース設定
- (任意) `python -m code2map` 実行のための `__main__.py` 追加
- (任意) 旧バージョン (`versions/v0.1.x`) を別リポジトリ or タグ管理へ移行
