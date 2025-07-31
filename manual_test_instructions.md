# AIチャット機能の手動テスト手順

## 1. アプリケーションの起動
```bash
python app.py
```

## 2. ブラウザでテスト

1. http://localhost:5001 にアクセス
2. Geminiモデルを選択（ラジオボタン）
3. 「シナリオ一覧」をクリック
4. 任意のシナリオをクリック

## 3. ブラウザコンソールでデバッグ

F12キーでデベロッパーツールを開き、Consoleタブで以下を実行：

```javascript
// APIエンドポイントを直接テスト
fetch('/api/async/scenario/stream', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.csrfManager?.getToken() || ''
    },
    body: JSON.stringify({
        message: 'テストメッセージ',
        model: localStorage.getItem('selectedModel') || 'gemini/gemini-1.5-flash',
        scenario_id: 'scenario1',
        is_initial: false
    })
})
.then(response => {
    console.log('Response status:', response.status);
    
    // SSEストリームを読み取る
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    function processStream() {
        reader.read().then(({done, value}) => {
            if (done) {
                console.log('Stream complete');
                return;
            }
            
            const chunk = decoder.decode(value);
            console.log('Received chunk:', chunk);
            
            // 続きを読む
            processStream();
        });
    }
    
    processStream();
})
.catch(error => console.error('Error:', error));
```

## 4. 期待される結果

1. コンソールに「Received chunk:」でSSEデータが表示される
2. data: {"content": "..."} の形式でAIの応答が流れてくる
3. 最後に data: {"status": "complete"} が表示される

## 5. エラーの場合

- Network タブで `/api/async/scenario/stream` のリクエストを確認
- Response Headers が `Content-Type: text/event-stream` になっているか確認
- Response タブでSSEデータが表示されているか確認

## 6. サーバーログの確認

別のターミナルで：
```bash
tail -f app.log
```

以下のようなログが表示されるはず：
- `=== Received request to /api/async/scenario/stream ===`
- `Calling Gemini with model: gemini/gemini-1.5-flash`
- `Got response: ...`