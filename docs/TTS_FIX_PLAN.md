# Gemini TTS 機能の修正計画

## 問題の概要

現在、Gemini TTSが動作していない原因：
- `from google import genai` という誤ったインポート文
- 正しくは `import google.generativeai as genai`

## 影響箇所

1. **text_to_speech関数** (app.py:1704行目)
   - TTSの音声合成機能

2. **generate_character_image関数** (app.py:2027行目)
   - 画像生成機能（同じインポートエラー）

## 修正内容

### 1. インポート文の修正

```python
# 間違い
from google import genai
from google.genai import types

# 正しい
import google.generativeai as genai
# typesは別途インポートが必要
```

### 2. API呼び出しの修正

現在のコードは新しいGemini SDK (google-genai)の形式を使用しているが、実際にインストールされているのは旧SDK (google-generativeai)の可能性がある。

## 推奨される修正手順

1. **依存関係の確認**
   - requirements.txtで正しいパッケージが指定されているか確認
   - google-genaiパッケージがインストールされているか確認

2. **コードの修正**
   - インポート文を修正
   - API呼び出しを適切なSDKバージョンに合わせて調整

3. **テスト**
   - test_gemini_tts.pyで動作確認
   - 各音声タイプでの動作確認

## 注意事項

- Gemini TTS機能は比較的新しい機能なので、SDKのバージョンによってAPIが異なる可能性がある
- 公式ドキュメントを参照して最新のAPI仕様を確認する必要がある