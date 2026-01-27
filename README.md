# code2map
**Transform large source code into semantic maps for AI-driven analysis and review.**
巨大なソースコードを、AI解析・レビュー向けの「意味的マップ（索引＋分割片）」に変換するツールです。

---

## Why / なぜ作るのか
2000行を超えるような巨大ファイルは、人間にとってもAIにとっても「全体像を見失いやすい」形です。
code2map は、ソースコードを **意味的にまとまった単位**に分割し、**Markdownの索引（地図）**を生成することで、次を実現します。

- AIが「どこに何があるか」を迷わず参照できる
- 設計書（Markdown）→分割コードの順で読みやすくなる
- 指摘箇所を **元ファイルの行番号**へ確実に戻せる

> 分割されたコード片は **コンパイル/実行を目的としません**。
> 目的は「読みやすさ」と「レビュー精度」です。

---

## What it does / できること（ゴール）
入力されたソース（例: `*.java`, `*.py`）から、主に次を生成します。

### 1) `INDEX.md`（人間 & AI向け）
- 関数 / クラスの一覧（目次）
- 役割の1行説明
- **元ファイルの行範囲（start–end）**
- 分割ファイルへのリンク
- 依存関係（参照クラス、設定、外部I/O）メモ

### 2) `parts/`（分割されたソース片）
- 元の拡張子を維持（`.java`, `.py` など）
- 各ファイル先頭に、必ず「元ファイル名」「行範囲」「注意書き」を付与
- 意味的なまとまり（クラス、メソッド群、処理フェーズなど）で分割

### 3) `MAP.json`（機械可読な対応表）
- シンボル（例: `FooService#doWork`）
- 元ファイル名、開始/終了行
- 分割ファイル名
などの対応関係を出力します。

---

## What it does NOT do / やらないこと（重要）
- ❌ 分割後のソースを **ビルド可能**にする
- ❌ 依存解決（import補完、参照先の自動統合）
- ❌ フォーマッタやLinterの代替
- ❌ 生成物を「正しい設計書」にする（※設計書は別途用意するのが前提）

code2mapは「実行するための再構成」ではなく、**レビュー・解析のための再構成**です。

---

## Output format / 出力フォーマット（例）
### `INDEX.md` 例（イメージ）
```md
# Index: FooService.java

## Classes
- FooService (L1–L980) → parts/FooService.class.java

## Methods
- FooService#doWork (L210–L356) → parts/FooService_doWork.java
  - role: main workflow for order processing
  - calls: BarRepository#findById, BazClient#post
  - side effects: DB update, external API call
```

### `parts/*` 例（先頭ヘッダのイメージ）
```java
// code2map fragment (non-buildable)
// original: src/main/java/.../FooService.java
// lines: 210-356
// symbol: FooService#doWork
// notes: references BarRepository, BazClient, OrderDto
```

### `MAP.json` 例（イメージ）
```json
[
  {
    "symbol": "FooService#doWork",
    "type": "method",
    "original_file": "FooService.java",
    "original_start_line": 210,
    "original_end_line": 356,
    "part_file": "parts/FooService_doWork.java",
    "checksum": "sha256_hash_of_content"
  }
]
```

---

## Naming conventions / 命名規則（おすすめ）
- `parts/<ClassName>.class.<ext>`：クラス全体を保持する断片（必要なら）
- `parts/<ClassName>_<methodName>.<ext>`：主要メソッド単位
- 生成物が衝突する場合は `__<hash>` を付加（例: `Foo_doWork__a1b2.java`）

---

## Usage / 使い方（予定）
CLIは `uv run code2map build <input_file> --out <output_dir>` を想定しています（Spec/Planに準拠）。

## Status / 現在のステータス
- ✅ **v0.1.0 MVP Released**: 基本実装完了。Python・Java 両言語対応。
- インストール可能: `uv sync` または `uv sync --all-extras`

---

## セットアップ

### 前提条件
- Python 3.9 以上
- [uv](https://docs.astral.sh/uv/) (推奨パッケージマネージャー)

### インストール
```bash
# リポジトリクローン
git clone https://github.com/example/code2map.git
cd code2map

# uv で依存関係インストール（仮想環境も自動作成）
uv sync --all-extras

# 動作確認
uv run code2map --help
uv run pytest
```

---

## Quick Start / 使い方

### 基本的な使用方法
```bash
# Python ファイルをマッピング
uv run code2map build path/to/LargeService.py --out ./code2map-out

# Java ファイルをマッピング
uv run code2map build path/to/LargeService.java --out ./code2map-out

# 出力確認
cat code2map-out/INDEX.md
ls code2map-out/parts/
cat code2map-out/MAP.json
```

### オプション一覧
```bash
uv run code2map build --help

# 主なオプション:
# --out <DIR>         出力ディレクトリ（デフォルト: ./code2map-out）
# --lang {java,python} 言語明示指定（省略時は拡張子から自動検出）
# --verbose           詳細ログ出力
# --dry-run           ファイル生成せず計画表示のみ
```

### 具体例
```bash
# 1. ドライラン（何が生成されるか確認）
uv run code2map build src/main/java/OrderService.java --dry-run

# 2. 詳細ログ付きで実行
uv run code2map build src/main/java/OrderService.java --out ./review --verbose

# 3. 生成物確認
cat review/INDEX.md           # 索引・役割・依存関係を表示
ls review/parts/              # 分割されたコード片一覧
cat review/MAP.json           # 行番号対応表（JSON形式）
```

### 推奨ワークフロー（AIレビュー）
1. `uv run code2map build <file> --out ./review` で分割・索引生成
2. `review/INDEX.md` をAIに読ませ、参照構造を理解させる
3. 詳細な指摘は `review/MAP.json` で元ファイル行番号へマップ
4. 指摘された行範囲を元ファイルで修正

---

## Usage / 使い方（予定）
- 分割後のコードは**ビルド不可**（import補完なし）
- **依存解析の正確性**: 静的解析のみ。動的ディスパッチ、リフレクションは考慮しない。
- 初期実装: **Java** と **Python** のみサポート。他言語は今後の拡張で対応。
- **意味的分割**: 初期段階ではクラス/メソッド単位のみ。処理フェーズ単位の分割は後続フェーズに実装予定。
- **入力スコープ**: MVPでは単一ファイルのみ。ディレクトリ単位の解析は後続フェーズ。
- **警告の出力先**: MVPでは警告は `INDEX.md` と `stderr` のみに出力し、`MAP.json` には含めない。

---

## Roadmap / 今後やりたいこと
### Phase 1-4: 基本実装（6-8週間）
- [ ] プロジェクト初期化、CLI基盤構築
- [ ] Python/Javaパーサ実装（AST解析）
- [ ] INDEX.md, parts/, MAP.json 生成ロジック
- [ ] ユニット・統合テスト、ドキュメント完成

### Phase 5+: 拡張
- [ ] 「意味的まとまり」判定の強化（フェーズ分割、例外・I/O境界の抽出）
- [ ] `INDEX.md` の品質向上（呼び出し関係のグラフ化、依存の推定精度向上）
- [ ] GitHub Actions での自動生成（PR ごとに索引生成）
- [ ] 生成物の差分比較（どのシンボルの行範囲が変わったか、変更影響度の可視化）
- [ ] C++, Go, Rust, TypeScript などの言語サポート拡張
- [ ] Web UI: ブラウザ上での INDEX.md インタラクティブ閲覧

---

## Contributing / コントリビュート
PR / Issues歓迎です。
「このコードはこう分割したい」「この言語を追加したい」など、具体例があると助かります。

---

## License
TBD（例: MIT / Apache-2.0）
