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
- ✅ 分割後のソースを **ビルド可能**にする  
- ✅ 依存解決（import補完、参照先の自動統合）  
- ✅ フォーマッタやLinterの代替  
- ✅ 生成物を「正しい設計書」にする（※設計書は別途用意するのが前提）

code2mapは「実行するための再構成」ではなく、**レビュー・解析のための再構成**です。

---

## Output format / 出力フォーマット（案）
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
    "original_file": "FooService.java",
    "original_start_line": 210,
    "original_end_line": 356,
    "part_file": "parts/FooService_doWork.java"
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
## Status / 現在のステータス
- ⚠️ **WIP (Work In Progress)**: 仕様・計画策定段階。実装未開始。
- 実装予定: 2026年1月～3月（約6-8週間）

---

## Installation / インストール（予定）
> 実装後に記述予定。以下は想定フロー：
```bash
pip install code2map
```

## Quick Start / クイックスタート（予定）
```bash
# 単一ファイルをマッピング
code2map build path/to/BigFile.java --out ./code2map-out

# 出力を確認
cat code2map-out/INDEX.md
ls code2map-out/parts/
cat code2map-out/MAP.json
```

### 想定出力構造
```
code2map-out/
├── INDEX.md              # AI/人間向け索引（Markdown）
├── MAP.json              # 機械可読な対応表
└── parts/
    ├── FooService.class.java      # クラス全体
    ├── FooService_doWork.java     # メソッド単位
    ├── FooService_validate.java
    └── ...
```

### 具体例
```bash
# 2000行のJavaファイルを処理
code2map build ./src/main/java/com/example/LargeService.java --out ./docs/code-map

# 出力:
# docs/code-map/INDEX.md - クラス/メソッド一覧、呼び出し関係、副作用情報
# docs/code-map/parts/* - 分割されたコード片（各々にメタデータヘッダ付き）
# docs/code-map/MAP.json - 行番号とファイルの対応表
```

---

## Workflow / 推奨ワークフロー（AIレビュー）
1. `code2map` で `INDEX.md` と `parts/` を生成
   ```bash
   code2map build src/main/java/YourService.java --out ./review
   ```
2. 先に「設計書Markdown」をAIに読ませる（目的・制約・不変条件・境界条件）
3. 次に `INDEX.md` を読ませ、参照すべき断片へ誘導
4. AIの指摘は `MAP.json` を使い、元ファイルの行番号へ戻して修正
   - 例: "FooService#doWork のロジックが複雑" → `MAP.json` で `parts/FooService_doWork.java` へマッピング → 元ファイルのL210-L356を修正

## Limitations / 既知の制限事項
- 分割後のコードは**ビルド不可**（import補完なし）
- **依存解析の正確性**: 静的解析のみ。動的ディスパッチ、リフレクションは考慮しない。
- 初期実装: **Java** と **Python** のみサポート。他言語は今後の拡張で対応。
- **意味的分割**: 初期段階ではクラス/メソッド単位のみ。処理フェーズ単位の分割は後続フェーズに実装予定。

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
