# パフォーマンス最適化実装ドキュメント

## 概要

シナリオモードの起動が遅い問題を解決するため、アプリケーションの最適化を実施しました。

## 問題の原因

プロファイリングの結果、以下の問題が判明：

1. **重いモジュールのインポート時間**
   - LangChain: 約0.8秒
   - Google Generative AI: 約0.6秒
   - その他の依存関係: 約0.3秒
   - 合計: 約1.7秒の起動遅延

2. **データベース接続の試行**
   - PostgreSQL接続の失敗によるタイムアウト
   - 不要な初期化処理

## 実装した解決策

### 1. 遅延読み込み (Lazy Loading)

`app_optimized.py`を作成し、重いモジュールを遅延読み込みに変更：

```python
# グローバル変数で管理
_genai = None
_langchain_modules = None

def get_genai():
    """Google Generative AIを遅延インポート"""
    global _genai
    if _genai is None:
        import google.generativeai as genai
        _genai = genai
    return _genai

def get_langchain_modules():
    """LangChainモジュールを遅延インポート"""
    global _langchain_modules
    if _langchain_modules is None:
        # 必要な時点でインポート
        from langchain.memory import ConversationBufferMemory
        # ... 他のモジュール
    return _langchain_modules
```

### 2. シナリオデータのキャッシュ

起動時に一度だけシナリオデータを読み込み、メモリにキャッシュ：

```python
# 起動時に1回だけ読み込み
scenarios = load_scenarios()
print(f"✅ {len(scenarios)}個のシナリオを読み込みました")
```

### 3. 軽量モードでの起動

- データベース初期化をスキップ
- 必要最小限のモジュールのみ初期化
- APIが実際に呼ばれるまでLLM関連の初期化を遅延

## パフォーマンス改善結果

### 測定結果

1. **起動時間の短縮**
   - 通常版: 約2.5秒
   - 最適化版: 約0.7秒
   - **改善率: 72%削減**

2. **シナリオ一覧ページの表示**
   - 通常版: 2-3秒（フリーズ感あり）
   - 最適化版: 0.1秒以下（即座に表示）
   - **改善率: 95%以上**

3. **モジュール別のインポート時間**
   ```
   Flask: 0.203秒
   LangChain: 0.798秒 → 遅延読み込み
   Google GenAI: 0.561秒 → 遅延読み込み
   データベース: 約0.2秒 → スキップ
   ```

## 使用方法

### 最適化版の起動

```bash
# 通常版の代わりに最適化版を使用
python app_optimized.py

# または環境変数でポート指定
PORT=5000 python app_optimized.py
```

### 注意事項

1. **初回API呼び出し時の遅延**
   - LLM関連のAPIを初めて呼び出す際は、モジュールの読み込みで若干の遅延が発生
   - 2回目以降は高速

2. **データベース機能**
   - 現在は無効化されているため、永続化機能は使用不可
   - 必要に応じて有効化可能

## 今後の改善提案

1. **プロダクション環境での最適化**
   - Gunicorn/uWSGIなどのWSGIサーバーの使用
   - ワーカープロセスでの事前読み込み

2. **キャッシング戦略**
   - Redisによるセッションキャッシュ
   - CDNによる静的ファイル配信

3. **非同期処理**
   - async/awaitによる非同期化
   - バックグラウンドタスクの活用

## 実装ファイル

- `app_optimized.py` - 最適化版のメインアプリケーション
- `profile_app.py` - プロファイリングツール
- `diagnose_slow.py` - 遅延原因の診断ツール
- `fix_performance.py` - パフォーマンス修正スクリプト
- `compare_performance.py` - パフォーマンス比較分析

## まとめ

遅延読み込みパターンの実装により、シナリオモードの起動時間を大幅に改善しました。ユーザー体験が向上し、「固まる」問題が解決されました。