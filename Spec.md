# code2map 仕様書 (Spec.md)

## 概要
code2map は、巨大なソースコードファイルを意味的に分割し、AI解析・レビュー向けの「意味的マップ（索引＋分割片）」を生成するツールです。主な目的は、コードの全体像を把握しやすくし、レビュー精度を向上させることです。分割されたコードはコンパイル/実行を目的とせず、読みやすさと参照性を重視します。

## 機能要件
### 入力
- **対象ファイル**: 単一のソースファイル（例: `*.java`, `*.py`）。初期実装ではJavaとPythonをサポート。
- **スコープ**: MVPでは単一ファイルのみ。ディレクトリ単位・複数ファイル対応は将来拡張。
- **形式**: テキストファイル。UTF-8エンコーディングを前提。
- **サイズ**: 2000行以上の巨大ファイルを想定。

### 出力
ツールは指定された出力ディレクトリに以下のファイルを生成します。

#### 1. INDEX.md
- **目的**: 人間およびAI向けの索引ファイル。Markdown形式。
- **内容**:
  - クラス一覧（クラス名、行範囲、分割ファイルへのリンク）。
  - メソッド一覧（メソッド名、行範囲、分割ファイルへのリンク）。
  - シンボル詳細（抽出可能な場合）:
    - **役割 (Role)**: Docstring/Javadocの先頭行または要約。
    - **呼び出し (Calls)**: メソッド内で呼び出している他のメソッドやクラス（静的解析に基づくヒューリスティック）。
    - **副作用 (Side Effects)**: I/O操作、DB更新などの主要な処理（キーワードマッチング等のヒューリスティック判定）。
- **フォーマット例**:
  ```markdown
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
  - **衝突回避**: Javaのオーバーロード等で名前が重複する場合、パラメータ型情報またはMD5ハッシュの一部を付与して一意性を保つ（例: `Foo_doWork__a1b2.java`）。
- **各ファイルのヘッダ**:
  - 元ファイル名
  - 行範囲 (Start-End)
  - シンボル名
  - 注意書き（依存クラス名など、ASTから抽出したコンテキスト情報）
- **例**:
  ```java
  // code2map fragment (non-buildable)
  // original: src/main/java/.../FooService.java
  // lines: 210-356
  // symbol: FooService#doWork
  // notes: references BarRepository, BazClient, OrderDto
  ```

#### 3. MAP.json
- **目的**: 機械可読な対応表。JSON形式。生成物の差分検知やツール連携用。
- **内容**: シンボルごとのオブジェクト配列。
- **スキーマ**:
  ```json
  [
    {
      "symbol": "FooService#doWork",
      "type": "method", // class, method, function
      "original_file": "FooService.java",
      "original_start_line": 210,
      "original_end_line": 356,
      "part_file": "parts/FooService_doWork.java",
      "checksum": "sha256_hash_of_content" // 内容変更検知用
    }
  ]
  ```

### CLI仕様
- **コマンド**: `code2map build <input_file> --out <output_dir>`
- **オプション**:
  - `--out`: 出力ディレクトリ（デフォルト: `./code2map-out`）
  - `--lang`: 言語指定（java, python）（省略時は自動検出。下記参照）
  - `--verbose`: 詳細ログ出力
  - `--dry-run`: ファイル書き込みを行わず、計画のみ表示
- **終了コード**:
  - `0`: 正常終了
  - `1`: 致命的エラー（入力ファイル不在、出力先書き込み不可、パーサー選択不能）
  - `2`: 部分成功（パースエラーが発生したが、部分的に出力を生成）

#### 言語自動検出
`--lang` が省略された場合、入力ファイルの拡張子から言語を判定する。
| 拡張子 | 言語 |
|--------|------|
| `.java` | Java |
| `.py` | Python |

上記に一致しない場合はエラー終了（終了コード `1`）し、`--lang` オプションでの明示指定を促すメッセージを出力する。

#### `--dry-run` 出力仕様
`--dry-run` 指定時はファイル書き込みを行わず、以下をstdoutに出力する:
- 検出したシンボル一覧（名前、種別、行範囲）
- 生成予定のファイル一覧（INDEX.md, parts/*, MAP.json のパス）
警告がある場合は `stderr` に出力する（MVP方針に準拠）。

#### 出力ディレクトリの動作
- 出力ディレクトリが存在しない場合: 自動作成する。
- 出力ディレクトリが既に存在する場合: 既存ファイルを**上書き**する。ただし、code2mapが生成しないファイル（ユーザーが手動で配置したファイル等）は削除しない。
- `parts/` サブディレクトリも同様に上書き動作とする。

### 非機能要件
- **パフォーマンス**: 数千行のファイルを数秒で処理。
- **正確性**: ASTベースの解析を行い、正規表現による簡易解析は避ける。MVPは言語別ライブラリ（Python: ast / Java: javalang）で実装し、Tree-sitterは将来の精度・拡張性強化で採用する。
- **拡張性**: 言語定義（Grammar）を追加するだけで新言語に対応できるアーキテクチャとする。
- **エラー処理**: パースエラー時も可能な限り部分的に解析を続行するか、明確なエラー箇所を示す。
- **エンコーディング**: 入力・出力ともUTF-8を前提とする。出力ファイルはBOMなしUTF-8で書き出す。

### パッケージ配布仕様
- **パッケージ名**: `code2map`
- **インストール**: `pip install code2map`
- **エントリーポイント**: `code2map` コマンドとして実行可能にする（`pyproject.toml` の `[project.scripts]` で定義）。
- **最小Python版**: Python 3.9+

## 技術スタック（推奨）
- **言語**: Python 3.9+
- **パーサー**:
  - **MVP**: 言語別ライブラリ（Python: `ast`, Java: `javalang`）
  - **拡張**: **Tree-sitter** (python bindings)
  - **選定基準**: 実装速度（MVP） vs パフォーマンス/拡張性（Tree-sitter）
- **ログ出力**: logging (標準ライブラリ)
- **テストフレームワーク**: pytest
- **CI/CD**: GitHub Actions

## 制約 & ヒューリスティック
- 分割後のコードはビルド不可（import補完なし）。
- **依存解析の限界**: "Calls" や "Side Effects" はあくまで静的解析による推定であり、100%の正確性を保証しない（動的ディスパッチやリフレクションは考慮しない）。
- 設計書の生成は別途前提。

### Side Effects 検出キーワード（ヒューリスティック）
INDEX.md の `side effects` 欄は、以下のキーワードパターンをメソッド本体内で検出した場合に記載する。

| カテゴリ | 検出キーワード例（Java） | 検出キーワード例（Python） |
|---------|------------------------|--------------------------|
| DB操作 | `save`, `update`, `delete`, `insert`, `persist`, `flush`, `commit` | `save`, `update`, `delete`, `insert`, `commit`, `execute` |
| 外部API | `Http`, `Client`, `RestTemplate`, `WebClient`, `fetch`, `post`, `put` | `requests.`, `http`, `urllib`, `fetch`, `post`, `put` |
| ファイルI/O | `FileWriter`, `OutputStream`, `write`, `PrintWriter` | `open(`, `write`, `Path`, `shutil` |
| ログ出力 | `log.`, `logger.` | `logging.`, `logger.`, `print(` |
| 例外送出 | `throw new` | `raise` |

キーワードリストは設定で拡張可能にすることを将来検討する（MVPでは固定）。

### Role 欄の抽出ルール
- **Java**: Javadocコメント（`/** ... */`）の最初の文（ピリオドまたは改行で区切る）を抽出。
- **Python**: docstring（`"""..."""` または `'''...'''`）の最初の行を抽出。
- **docstring/Javadoc が存在しない場合**: `role` 欄は省略する（空文字やプレースホルダは出力しない）。

### Checksum 仕様
MAP.json の `checksum` フィールドは、分割されたコード片（ヘッダコメントを除く元ソース部分）の **SHA-256 ハッシュ値**（16進数文字列、小文字）を格納する。

### ネスト構造の命名規則
- **ネストクラス**: `parts/<OuterClass>_<InnerClass>.class.<ext>`
- **ネストクラスのメソッド**: `parts/<OuterClass>_<InnerClass>_<methodName>.<ext>`
- **ネスト関数（Python）**: 親関数のパートに含める（個別ファイルには分割しない）。

## エラーハンドリング
### パースエラー時の動作
1. **部分的解析継続**: パースエラー発生時、既に抽出されたシンボルで出力生成。
2. **エラー情報の記録**: エラー箇所を `INDEX.md` 内に `[WARNING]` コメントで記載。
3. **詳細ログ**: `--verbose` 時、stderr に解析失敗行番号と理由を出力。
4. **フォールバック**: パーサー選択ミスの場合、`--lang` オプションで手動指定可能。

### ファイル I/O エラー
- 入力ファイル不存在: 明確なエラーメッセージ + 終了
- 出力ディレクトリ書き込み不可: エラーメッセージ + 終了
- エンコーディングエラー（非UTF-8）: 警告メッセージ + ベストエフォート処理

### 警告の出力先（MVP方針）
- **INDEX.md**: `[WARNING]` を含むコメントで警告内容を記録する。
- **stderr**: `--verbose` の場合は詳細ログを出力する。
- **MAP.json**: MVPでは警告情報を含めない（スキーマを固定して機械連携を優先）。

## 言語別対応範囲（初期実装）
### Java
- **対応構文**: クラス、メソッド、フィールド（public/private）、ネストクラス
- **非対応**: アノテーション詳細解析、ジェネリクス型パラメータの完全マッピング
- **依存抽出**: import文、メソッド呼び出し（シンプルなヒューリスティック）

### Python
- **対応構文**: クラス、関数、メソッド、デコレータ
- **非対応**: ダイナミック呼び出し（eval, exec）、型アノテーション詳細
- **依存抽出**: import文、関数/メソッド呼び出し（ヒューリスティック）

### 拡張言語（Phase 5+）
- C++, Go, Rust, TypeScript: Tree-sitter Grammar 追加で対応予定

---

## 実装評価 (v0.1.0)

### 評価概要
- **テスト**: 19/19 PASS（0.55秒）
- **カバレッジ**: 87%（目標80%をクリア）
- **対応言語**: Python, Java（仕様通り）
- **出力物**: INDEX.md, parts/, MAP.json（全て生成確認済）

### 仕様適合状況

| 仕様項目 | 状態 | 備考 |
|---------|------|------|
| CLI `build` コマンド | ✅ 適合 | argparse によるサブコマンド実装 |
| `--out`, `--lang`, `--verbose`, `--dry-run` | ✅ 適合 | 全オプション実装済 |
| 終了コード (0/1/2) | ✅ 適合 | 正常=0, エラー=1, 警告あり=2 |
| 言語自動検出 | ✅ 適合 | 拡張子テーブルで判定 |
| INDEX.md 生成 | ✅ 適合 | Classes/Methods/Functions セクション、role/calls/side effects 欄 |
| parts/ 生成 | ✅ 適合 | ヘッダ付き、命名規則準拠 |
| MAP.json 生成 | ✅ 適合 | SHA-256 checksum 含む |
| ネストクラス命名 | ✅ 適合 | `OuterClass_InnerClass` 形式 |
| ネスト関数（Python） | ✅ 適合 | 親シンボルに含め個別分割しない |
| パースエラー時の部分解析 | ⚠️ 一部 | エラー時に空リスト返却。既に抽出済みシンボルの返却は未実装 |
| UTF-8 / エンコーディング | ✅ 適合 | `errors="replace"` + U+FFFD検出で警告 |
| `--dry-run` 出力 | ✅ 適合 | シンボル一覧 + 生成予定ファイル一覧を stdout に出力 |
| 出力ディレクトリ上書き動作 | ✅ 適合 | `mkdir(parents=True, exist_ok=True)` + ファイル上書き |
| Checksum (SHA-256) | ✅ 適合 | ヘッダ除外の元ソース部分をハッシュ |
| Role 欄抽出 | ✅ 適合 | docstring/Javadoc から最初の文を抽出、なければ省略 |

### 仕様との乖離・改善点

#### 1. パッケージ配布形式 (低リスク)
- **仕様**: `pyproject.toml`（PEP 621）でエントリーポイント定義
- **実装**: `setup.py` で定義（動作上は問題なし）
- **影響**: 機能的に同等だが、現代のPythonパッケージング標準に合わせるため `pyproject.toml` への移行を推奨

#### 2. Side Effects 検出キーワードの差異 (中リスク)
- **仕様**: 言語別に細分化されたキーワードテーブル（DB操作、外部API、ファイルI/O、ログ出力、例外送出の5カテゴリ）
- **実装**: 言語非依存の4カテゴリ（file io, stdout, network, db）で簡略化
- **不足キーワード**: `save`, `persist`, `flush`, `commit`, `requests.`, `urllib`, `shutil`, `logging.`, `logger.`, `throw new`, `raise` 等
- **影響**: 一部の副作用が検出されない可能性がある。Spec のキーワードテーブルに合わせた拡充を推奨

#### 3. パース失敗時の部分解析 (低リスク)
- **仕様**: パースエラー発生時、既に抽出されたシンボルで出力生成
- **実装**: Python/Java パーサーともに、パースエラー時は空のシンボルリストを返却
- **影響**: 構文エラーのあるファイルでは出力が空になる。MVP では許容範囲だが、将来的に部分抽出に対応すべき

#### 4. 未実装のファイル (低リスク)
- **`models/metadata.py`**: Plan に記載があるが未作成。Symbol クラスで代替しており実用上問題なし
- **`utils/lang_detect.py`**: Plan に記載があるが、cli.py 内に `_detect_lang()` として直接実装。モジュール分割は将来のリファクタリングで対応可
- **`CONTRIBUTING.md`**: Plan Phase 4 に記載があるが未作成

#### 5. `_ignore_new_symbol` の未使用コード (極低リスク)
- `python_parser.py:17` の `_ignore_new_symbol` フィールドが定義されているが、値を変更するコードがない
- デッドコード。削除推奨

#### 6. Java コンストラクタの呼び出し関係未抽出 (低リスク)
- メソッドには `filter(MethodInvocation)` で calls を抽出しているが、コンストラクタ（`<init>`）には同処理がない
- コンストラクタ内の呼び出し関係が INDEX.md に反映されない
