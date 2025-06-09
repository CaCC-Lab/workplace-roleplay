#!/bin/bash

# TTSエンドポイントのテストスクリプト

echo "=== TTS API テスト ==="

# 1. 利用可能な音声の一覧を取得
echo -e "\n1. 利用可能な音声の一覧を取得:"
curl -s http://localhost:5001/api/tts/voices | python3 -m json.tool

# 2. TTSリクエストのテスト（OpenAI API）
echo -e "\n\n2. TTSリクエストのテスト:"
curl -X POST http://localhost:5001/api/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "こんにちは、音声合成のテストです。",
    "voice": "nova"
  }' | python3 -m json.tool

# 3. 長いテキストでのテスト
echo -e "\n\n3. 長いテキストでのテスト:"
curl -X POST http://localhost:5001/api/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "本日はお忙しい中、お時間をいただきありがとうございます。今回のプロジェクトについて、進捗状況をご報告させていただきます。",
    "voice": "shimmer"
  }' | python3 -m json.tool

# 4. エラーケースのテスト（テキストなし）
echo -e "\n\n4. エラーケースのテスト（テキストなし）:"
curl -X POST http://localhost:5001/api/tts \
  -H "Content-Type: application/json" \
  -d '{"voice": "nova"}' | python3 -m json.tool

echo -e "\n\n=== テスト完了 ==="