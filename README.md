# code2map
**Transform large source code into semantic maps for AI-driven analysis and review.**  
巨大なソースコードを、AI解析・レビュー向けの「意味的マップ（索引＋分割片）」に変換するツール。

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
> このREADMEは初期テンプレです。CLI仕様は固まり次第更新します。

想定CLI:
```bash
code2map build path/to/BigFile.java --out ./code2map-out
```

想定出力:
```
code2map-out/
  INDEX.md
  MAP.json
  parts/
    FooService_doWork.java
    ...
```

---

## Workflow / 推奨ワークフロー（AIレビュー）
1. `code2map` で `INDEX.md` と `parts/` を生成
2. 先に「設計書Markdown」をAIに読ませる（目的・制約・不変条件・境界条件）
3. 次に `INDEX.md` を読ませ、参照すべき断片へ誘導
4. AIの指摘は `MAP.json` を使い、元ファイルの行番号へ戻して修正

---

## Roadmap / 今後やりたいこと
- [ ] Java/Pythonのパーサ統合（ASTベースの分割）
- [ ] 「意味的まとまり」判定の強化（フェーズ分割、例外・I/O境界の抽出）
- [ ] `INDEX.md` の品質向上（呼び出し関係、依存の推定）
- [ ] GitHub Actionsでの自動生成（PRごとに索引生成）
- [ ] 生成物の差分比較（どのシンボルの行範囲が変わったか）

---

## Contributing / コントリビュート
PR / Issues歓迎です。  
「このコードはこう分割したい」「この言語を追加したい」など、具体例があると助かります。

---

## License
TBD（例: MIT / Apache-2.0）
