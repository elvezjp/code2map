# code2map 実装計画 (Plan.md)

## 概要
code2map の実装を段階的に進める計画。主言語としてPythonを使用し、CLIツールとして開発。初期バージョンではJavaとPythonのソースコードを対象とする。

## 必要な技術・ライブラリ
- **言語**: Python 3.8+
- **CLI**: argparse (標準ライブラリ)
- **AST解析**:
  - Python: ast (標準ライブラリ)
  - Java: javalang (外部ライブラリ、pip install javalang)
- **ファイル操作**: os, pathlib (標準)
- **JSON出力**: json (標準)
- **Markdown生成**: 手動またはmarkdownライブラリ
- **テスト**: unittest (標準) または pytest

## ファイル構造
```
code2map/
├── main.py                 # エントリーポイント、CLI処理
├── parsers/
│   ├── base_parser.py      # 共通パーサー基底クラス
│   ├── java_parser.py      # Java AST解析
│   └── python_parser.py    # Python AST解析
├── generators/
│   ├── index_generator.py  # INDEX.md 生成
│   ├── parts_generator.py  # parts/ ディレクトリ生成
│   └── map_generator.py    # MAP.json 生成
├── utils/
│   └── file_utils.py       # ファイル操作ユーティリティ
├── tests/
│   ├── test_java.py
│   └── test_python.py
└── README.md               # プロジェクト説明
```

## 実装ステップ
### Phase 1: 基盤構築 (1-2週間)
1. **プロジェクト初期化**
   - ディレクトリ構造作成
   - requirements.txt 作成（依存ライブラリ）
   - main.py のスケルトン（CLI引数処理）

2. **共通基盤**
   - base_parser.py: シンボル抽出のインターフェース定義
   - file_utils.py: ファイル読み書き、行範囲抽出

### Phase 2: パーサー実装 (2-3週間)
3. **Pythonパーサー**
   - python_parser.py: astモジュールでクラス/メソッド抽出
   - 行番号取得、依存関係推定（import, 関数呼び出し）

4. **Javaパーサー**
   - java_parser.py: javalangでAST解析
   - クラス/メソッド/フィールド抽出
   - 行範囲と依存関係の取得

### Phase 3: 生成ロジック (2-3週間)
5. **INDEX.md 生成**
   - index_generator.py: Markdown形式の索引作成
   - クラス/メソッド一覧、リンク、説明文生成

6. **parts/ 生成**
   - parts_generator.py: ソース分割とヘッダ付与
   - 意味的まとまりの判定（初期はクラス/メソッド単位）

7. **MAP.json 生成**
   - map_generator.py: JSON対応表出力

### Phase 4: 統合とテスト (1-2週間)
8. **メイン処理統合**
   - main.py でパーサー選択、生成器呼び出し
   - エラー処理、出力ディレクトリ作成

9. **テスト実装**
   - サンプルJava/Pythonファイル作成
   - ユニットテスト（パーサー正確性、出力検証）
   - 統合テスト（CLI実行）

10. **ドキュメント更新**
    - README.md 更新（使い方詳細）
    - Spec.md/Plan.md 最終確認

## 意味的分割のロジック
- **初期実装**: クラス全体、メソッド単位で分割。
- **拡張**: 処理フェーズ（条件分岐、ループ）、I/O境界で分割。
- **判定基準**: ASTノードの種類、コメント、関数呼び出しの集中度。

## テスト計画
- **ユニットテスト**: 各パーサー、生成器の関数テスト。
- **統合テスト**: エンドツーエンド（入力ファイル→出力検証）。
- **エッジケース**: 空ファイル、無効構文、巨大ファイル。
- **CI**: GitHub Actionsで自動テスト。

## タイムライン
- **Phase 1**: 完了後、基本CLI動作確認。
- **Phase 2**: Java/Python両方でシンボル抽出可能に。
- **Phase 3**: 出力生成完了、動作確認。
- **Phase 4**: リリース準備。
- **総期間**: 約6-8週間（個人開発想定）。

## リスクと対策
- **AST解析の複雑さ**: 各言語のドキュメント参照、テスト駆動開発。
- **依存関係推定の不正確さ**: 初期はシンプルに、フィードバックで改善。
- **パフォーマンス**: 大ファイルでメモリ使用監視、必要時最適化。

## 拡張計画
- 新言語追加（JavaScript: acorn, C++: clang）
- 設定ファイル（分割粒度カスタム）
- GitHub Actions統合（PRごと自動生成）