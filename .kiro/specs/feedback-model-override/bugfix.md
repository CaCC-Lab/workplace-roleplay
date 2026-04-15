# Bugfix: フロントエンドが DEFAULT_MODEL を勝手に送信し FEEDBACK_MODEL を無視する

## Current Behavior（現在の動作）

本番では `FEEDBACK_MODEL=ollama/gemma4:31b-cloud` を設定しているが、シナリオのフィードバック画面右下に「使用モデル: gemini/gemini-2.5-flash-lite」と表示される。つまり **Ollama Gemma 4 が使われず Gemini Flash Lite が使われている**。

### 証拠

1. `static/js/model-selection.js:28`
   ```javascript
   if (!flags.model_selection && flags.default_model) {
       localStorage.setItem('selectedModel', flags.default_model);
   }
   ```
   → モデル選択UI無効時に DEFAULT_MODEL を自動で localStorage に書き込む

2. `static/js/model-selection.js:89`, `chat.js:35, 107, 258`, `scenario.js:114`
   → 同様のパターンで DEFAULT_MODEL を localStorage に自動保存

3. `static/js/scenario.js:296`
   ```javascript
   body: JSON.stringify({
       scenario_id: scenarioId,
       model: selectedModel  // localStorage から取得した DEFAULT_MODEL が送信される
   })
   ```

4. バックエンド `routes/scenario_routes.py`
   ```python
   selected_model = resolve_model("feedback", data.get("model"))
   ```
   `resolve_model()` は第2引数 (session_selected) を最優先するため、
   フロントが送った DEFAULT_MODEL が FEEDBACK_MODEL env よりも優先されてしまう。

## Expected Behavior（期待する動作）

**ユーザーが明示的にモデルを選択した場合のみ** `model` を送信する。
何も選んでいない場合は `model` を省略（または `null`）→ バックエンドが
`<MODE>_MODEL` env → `DEFAULT_MODEL` の順でフォールバック。

結果、`FEEDBACK_MODEL=ollama/gemma4:31b-cloud` が正しく効く。

## Unchanged Behavior（変更しない動作）

- モデル選択UIを有効にしている場合（ユーザーが明示的に選んだ場合）の挙動は不変
- バックエンドの `resolve_model()` ロジックは変更しない
- Gemini単独運用時（FEEDBACK_MODEL未設定）の動作は不変

## Root Cause（根本原因）

フロント側が「localStorage が空なら DEFAULT_MODEL を書き込む」というフォールバックロジックを持っており、その結果、**ユーザーが実際に選択していないモデル**がバックエンドに「UI選択」として送信されていた。これが Phase B で導入した `<MODE>_MODEL` env を上書きしてしまう。

## Fix Strategy（修正方針）

1. **モデル選択UI無効時は localStorage を能動的にクリア**
   - 既存ユーザーのブラウザに残った旧 DEFAULT_MODEL 値を除去するため
   - `model-selection.js` の `!flags.model_selection` 分岐を `setItem` → `removeItem` に変更

2. **各所の "デフォルトを localStorage に書き込む" 処理を削除**
   - `chat.js` / `scenario.js` / `model-selection.js` の該当箇所
   - 代わりにローカル変数で `window.DEFAULT_MODEL` をフォールバック利用するだけに留める

3. **ユーザーが `<select>` を明示変更した場合の保存は維持**（`addEventListener('change', ...)`）

### 修正対象

| ファイル | 行 | 修正 |
|---|---|---|
| `static/js/model-selection.js` | 27-29 | `setItem` → `removeItem`（旧値クリア） |
| `static/js/model-selection.js` | 87-90 | 削除（/api/models 取得後の自動保存を廃止） |
| `static/js/chat.js` | 33-37, 104-109, 256-259 | `localStorage.setItem` 行を削除 |
| `static/js/scenario.js` | 111-116 | `localStorage.setItem` 行を削除 |

修正後、`localStorage.getItem('selectedModel')` の結果は:
- ユーザー明示選択あり: 選択値
- それ以外: `null` → フロントは `model: null` 送信 → バックエンドが env/DEFAULT にフォールバック

## Test Strategy

- **手動**: 本番反映後、シナリオ実行 → フィードバック取得 → 右下の「使用モデル」が `ollama/gemma4:31b-cloud` に変わること
- **コード**: `localStorage.getItem` の null チェック後、`setItem` 呼び出しが無いこと
- **回帰**: モデル選択UI有効時に `<select>` 変更で保存される動作は従来どおり

## Risk Assessment

- **破壊的変更**: なし（localStorage を空にしてもバックエンドがフォールバックするため）
- **ロールバック**: revert で即戻る
- **副作用**: 既存ユーザーの localStorage に値が残っている場合は依然として送信される → 影響は「一度サイトを開いたユーザーでは依然バグる」。完全解消には localStorage.removeItem('selectedModel') を入れるか、送信側で無効化する
