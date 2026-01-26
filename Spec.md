# code2map 仕様書 (Spec.md)

## 概要
code2map は、巨大なソースコードファイルを意味的に分割し、AI解析・レビュー向けの「意味的マップ（索引＋分割片）」を生成するツールです。主な目的は、コードの全体像を把握しやすくし、レビュー精度を向上させることです。分割されたコードはコンパイル/実行を目的とせず、読みやすさと参照性を重視します。

## 機能要件
### 入力
- **対象ファイル**: 単一のソースファイル（例: `*.java`, `*.py`）。初期実装ではJavaとPythonをサポート。
- **形式**: テキストファイル。UTF-8エンコーディングを前提。
- **サイズ**: 2000行以上の巨大ファイルを想定。

### 出力
ツールは指定された出力ディレクトリに以下のファイルを生成します。

#### 1. INDEX.md
- **目的**: 人間およびAI向けの索引ファイル。Markdown形式。
- **内容**:
  - クラス一覧（クラス名、行範囲、分割ファイルへのリンク）。
  - メソッド一覧（メソッド名、行範囲、分割ファイルへのリンク、役割の1行説明、呼び出し先、サイドエフェクト）。
  - 依存関係のメモ（参照クラス、設定、外部I/O）。
- **フォーマット例**:
  ```
  # Index: FooService.java

  ## Classes
  - FooService (L1–L980) → parts/FooService.class.java

  ## Methods
  - FooService#doWork (L210–L356) → parts/FooService_doWork.java
    - role: main workflow for order processing
    - calls: BarRepository#findById, BazClient#post
    - side effects: DB update, external API call
  ```

#### 2. parts/ ディレクトリ
- **目的**: 分割されたソースコード片を格納。
- **ファイル命名規則**:
  - クラス全体: `parts/<ClassName>.class.<ext>`
  - メソッド単位: `parts/<ClassName>_<methodName>.<ext>`
  - 衝突時: `__<hash>` を付加（例: `Foo_doWork__a1b2.java`）。
- **各ファイルのヘッダ**:
  - 元ファイル名
  - 行範囲
  - シンボル名
  - 注意書き（参照先など）
- **例**:
  ```java
  // code2map fragment (non-buildable)
  // original: src/main/java/.../FooService.java
  // lines: 210-356
  // symbol: FooService#doWork
  // notes: references BarRepository, BazClient, OrderDto
  ```

#### 3. MAP.json
- **目的**: 機械可読な対応表。JSON形式。
- **内容**: シンボルごとのオブジェクト配列。
  - symbol: シンボル名（例: "FooService#doWork"）
  - original_file: 元ファイル名
  - original_start_line: 開始行
  - original_end_line: 終了行
  - part_file: 分割ファイル名
- **例**:
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

### CLI仕様
- **コマンド**: `code2map build <input_file> --out <output_dir>`
- **オプション**:
  - `--out`: 出力ディレクトリ（デフォルト: `./code2map-out`）
  - `--lang`: 言語指定（java, python）（自動検出可能なら省略）
- **例**:
  ```bash
  code2map build path/to/BigFile.java --out ./code2map-out
  ```

### 非機能要件
- **パフォーマンス**: 数千行のファイルを数秒で処理。
- **正確性**: 行範囲の正確なマッピング。ASTベースの解析を推奨。
- **拡張性**: 新言語の追加が容易。
- **エラー処理**: 無効な入力ファイル時は適切なエラーメッセージを出力。

## サポート言語
- **初期**: Java, Python
- **拡張**: 将来的に他の言語（JavaScript, C++など）

## 制約
- 分割後のコードはビルド不可（import補完なし）。
- 依存解決は行わない。
- 設計書の生成は別途前提。