# シナリオモード遅延問題の修正報告

## 問題

シナリオ一覧ページ（/scenarios）へのアクセスが**分単位**で遅延する深刻な問題が発生していました。

## 原因

`app.py`の`get_available_gemini_models()`関数内で`genai.list_models()`を呼び出していたことが原因でした。

```python
# 問題のコード（line 383）
models = genai.list_models()
```

このAPI呼び出しが：
- ネットワーク遅延
- タイムアウト
- Google APIサーバーの応答遅延

により、分単位でブロックしていました。

## 修正内容

`genai.list_models()`の呼び出しを削除し、固定のモデルリストを返すように変更しました。

```python
def get_available_gemini_models():
    """
    利用可能なGeminiモデルのリストを返す
    ※ genai.list_models()のブロッキング問題を修正
    """
    # 固定のモデルリストを返す（API呼び出しを避ける）
    default_models = [
        "gemini/gemini-1.5-pro",
        "gemini/gemini-1.5-flash",
        "gemini/gemini-1.5-pro-latest",
        "gemini/gemini-1.5-flash-latest"
    ]
    
    # API呼び出しをスキップして固定リストを返す
    return default_models
```

## 結果

- **修正前**: 分単位の遅延（タイムアウト）
- **修正後**: 2.7秒で応答

**改善率**: 95%以上（数分 → 数秒）

## テスト結果

```
シナリオ一覧ページへアクセス:
   ✅ 成功!
   応答時間: 2.762秒
   ステータス: 200

モデル一覧APIテスト:
   応答時間: 0.057秒
   ステータス: 200
   モデル数: 4
```

## 今後の改善案

1. **キャッシュの実装**
   - モデルリストを定期的に更新
   - タイムアウト付きで安全にAPI呼び出し

2. **非同期化**
   - ページ表示とAPI呼び出しを分離
   - バックグラウンドでモデルリストを更新

3. **設定ファイル化**
   - 利用可能なモデルを設定ファイルで管理
   - 環境変数で制御

## 関連ファイル

- `app.py` - 修正済み
- `fix_blocking_models.py` - 修正方法の説明
- `test_fixed_app.py` - 修正版のテスト
- `debug_*.py` - 問題調査用スクリプト

## まとめ

シナリオモードの分単位の遅延問題は、Google Gemini APIの`list_models()`呼び出しがブロッキングしていたことが原因でした。固定リストを使用することで、この問題を解決し、ユーザー体験を大幅に改善しました。