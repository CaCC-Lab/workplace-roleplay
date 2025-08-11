#!/bin/bash

# リアルタイム5AI議論システム実行スクリプト
# 複数のAIを並列で起動し、効率的な議論を実現

set -e

echo "🚀 リアルタイム5AI議論システムを起動します..."
echo "================================================"

# 必要な依存関係の確認
check_dependencies() {
    echo "📦 依存関係を確認中..."
    
    # Pythonバージョン確認
    if ! python3 --version | grep -E "3\.(8|9|10|11)" > /dev/null; then
        echo "❌ Python 3.8以上が必要です"
        exit 1
    fi
    
    # 必要なPythonパッケージ
    pip3 install -q asyncio dataclasses typing-extensions 2>/dev/null || true
    
    # AI CLIツールの確認（オプション）
    echo "🔍 利用可能なAI CLIツールを確認中..."
    
    if command -v gemini &> /dev/null; then
        echo "  ✅ Gemini CLI: 利用可能"
    else
        echo "  ⚠️ Gemini CLI: 未インストール"
    fi
    
    if command -v qwen &> /dev/null; then
        echo "  ✅ Qwen CLI: 利用可能"
    else
        echo "  ⚠️ Qwen CLI: 未インストール"
    fi
    
    if command -v codex &> /dev/null; then
        echo "  ✅ Codex CLI: 利用可能"
    else
        echo "  ⚠️ Codex CLI: 未インストール"
    fi
    
    echo ""
}

# 議論トピックの選択
select_topic() {
    echo "📋 議論トピックを選択してください:"
    echo "1) アーキテクチャ設計（Flask vs FastAPI）"
    echo "2) セキュリティ強化策"
    echo "3) パフォーマンス最適化"
    echo "4) 移行戦略とリスク管理"
    echo "5) カスタムトピック"
    
    read -p "選択 (1-5): " choice
    
    case $choice in
        1)
            TOPIC="architecture"
            TITLE="最適なアーキテクチャ選択"
            DESCRIPTION="Flask vs FastAPI vs Quartの比較と移行戦略"
            ;;
        2)
            TOPIC="security"
            TITLE="セキュリティ強化設計"
            DESCRIPTION="XSS, CSRF, 認証認可の包括的対策"
            ;;
        3)
            TOPIC="performance"
            TITLE="パフォーマンス最適化"
            DESCRIPTION="キャッシング、非同期処理、負荷分散の設計"
            ;;
        4)
            TOPIC="migration"
            TITLE="移行戦略とリスク管理"
            DESCRIPTION="段階的移行、ロールバック、モニタリング"
            ;;
        5)
            read -p "トピックタイトル: " TITLE
            read -p "説明: " DESCRIPTION
            TOPIC="custom"
            ;;
        *)
            echo "無効な選択です"
            exit 1
            ;;
    esac
}

# 議論時間の設定
set_duration() {
    echo ""
    echo "⏱️ 議論時間を設定してください:"
    echo "1) 5分（高速議論）"
    echo "2) 15分（標準議論）"
    echo "3) 30分（詳細議論）"
    echo "4) カスタム"
    
    read -p "選択 (1-4): " duration_choice
    
    case $duration_choice in
        1) DURATION=300 ;;
        2) DURATION=900 ;;
        3) DURATION=1800 ;;
        4) 
            read -p "議論時間（秒）: " DURATION
            ;;
        *)
            DURATION=900
            echo "デフォルト（15分）を使用します"
            ;;
    esac
}

# Pythonスクリプトの実行
run_discussion() {
    echo ""
    echo "🎯 議論を開始します..."
    echo "トピック: $TITLE"
    echo "説明: $DESCRIPTION"
    echo "制限時間: $((DURATION / 60))分"
    echo ""
    
    # 議論パラメータをJSONファイルに保存
    cat > /tmp/discussion_config.json << EOF
{
    "title": "$TITLE",
    "description": "$DESCRIPTION",
    "duration": $DURATION,
    "objectives": [
        "最適解の発見",
        "リスクの特定",
        "実装計画の策定"
    ],
    "constraints": [
        "既存システムとの互換性",
        "3ヶ月以内の実装",
        "ダウンタイム最小化"
    ]
}
EOF
    
    # Pythonスクリプトを実行
    python3 realtime_5ai_discussion.py
}

# 結果の表示
show_results() {
    echo ""
    echo "📊 議論結果を表示しています..."
    
    if [ -f "discussion_result.json" ]; then
        # 結果のサマリーを表示
        python3 -c "
import json
with open('discussion_result.json', 'r') as f:
    result = json.load(f)
    print(f\"\\n{'='*60}\")
    print(f\"📈 議論統計:\")
    print(f\"  - 所要時間: {result['duration']}秒\")
    print(f\"  - メッセージ数: {result['message_count']}\")
    print(f\"  - 平均応答時間: {result['average_response_time']:.2f}秒\")
    print(f\"\\n🤝 合意事項:\")
    for item in result.get('consensus', []):
        print(f\"  ✓ {item}\")
    print(f\"\\n💾 詳細結果: discussion_result.json\")
    print(f\"{'='*60}\\n\")
"
    fi
}

# HTMLビューアーの起動（オプション）
launch_viewer() {
    echo "🌐 HTMLビューアーを起動しますか？ (y/n)"
    read -p "> " launch_html
    
    if [ "$launch_html" = "y" ]; then
        # シンプルなHTTPサーバーを起動
        echo "📡 HTTPサーバーを起動中..."
        echo "ブラウザで http://localhost:8080/realtime_discussion_web.html を開いてください"
        python3 -m http.server 8080 --directory . &
        SERVER_PID=$!
        
        # macOSの場合は自動でブラウザを開く
        if [ "$(uname)" = "Darwin" ]; then
            sleep 2
            open "http://localhost:8080/realtime_discussion_web.html"
        fi
        
        echo ""
        echo "サーバーを停止するには Ctrl+C を押してください"
        wait $SERVER_PID
    fi
}

# メイン処理
main() {
    clear
    echo "╔════════════════════════════════════════════╗"
    echo "║   🤖 リアルタイム5AI議論システム v1.0      ║"
    echo "║   高速・並列・効率的なAI協調設計           ║"
    echo "╚════════════════════════════════════════════╝"
    echo ""
    
    check_dependencies
    select_topic
    set_duration
    run_discussion
    show_results
    launch_viewer
}

# トラップ設定（クリーンアップ）
trap 'echo ""; echo "🛑 議論を中断しました"; exit 1' INT TERM

# 実行
main