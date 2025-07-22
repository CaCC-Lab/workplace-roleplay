#!/usr/bin/env python3
"""
統合テストの構文エラーを一括修正するスクリプト
"""
import re

# ファイルを読み込み
with open('tests/test_app_integration_advanced.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 壊れた関数を修正
fixes = [
    # Unicode emoji test
    (r'    def test_unicode_emoji_handling\(self, csrf_client\):\s+"""Unicode絵文字の処理を確認"""\s+emoji_message = "こんにちは！😊🌟⭐️🎉🚀💖"\s+mock_llm\.invoke\.return_value = mock_response\s+with csrf_client\.session_transaction\(\) as sess:',
     '''    def test_unicode_emoji_handling(self, csrf_client, mock_all_external_apis):
        """Unicode絵文字の処理を確認"""
        emoji_message = "こんにちは！😊🌟⭐️🎉🚀💖"
        
        # グローバルモックを使用
        mock_llm = mock_all_external_apis['mock_llm']
        from langchain_core.messages import AIMessage
        mock_response = AIMessage(content="絵文字がたくさんですね！😄")
        mock_llm.invoke.return_value = mock_response
        
        with csrf_client.session_transaction() as sess:'''),
    
    # Malformed session data test
    (r'    def test_malformed_session_data\(self, csrf_client\):\s+"""不正なセッションデータでの処理を確認"""\s+with csrf_client\.session_transaction\(\) as sess:\s+# 不正なデータ形式をセッションに設定\s+sess\[\'chat_history\'\] = "不正なデータ形式"\s+sess\[\'chat_settings\'\] = \["リスト形式", "不正"\]\s+mock_llm\.invoke\.return_value = mock_response',
     '''    def test_malformed_session_data(self, csrf_client, mock_all_external_apis):
        """不正なセッションデータでの処理を確認"""
        with csrf_client.session_transaction() as sess:
            # 不正なデータ形式をセッションに設定
            sess['chat_history'] = "不正なデータ形式"
            sess['chat_settings'] = ["リスト形式", "不正"]
        
        # グローバルモックを使用
        mock_llm = mock_all_external_apis['mock_llm']
        from langchain_core.messages import AIMessage
        mock_response = AIMessage(content="復旧しました")
        mock_llm.invoke.return_value = mock_response'''),
    
    # Concurrent session access test
    (r'    def test_concurrent_session_access\(self, csrf_client\):\s+"""同一セッションでの並行アクセスの処理を確認"""\s+mock_llm\.invoke\.return_value = mock_response\s+with csrf_client\.session_transaction\(\) as sess:',
     '''    def test_concurrent_session_access(self, csrf_client, mock_all_external_apis):
        """同一セッションでの並行アクセスの処理を確認"""
        # グローバルモックを使用
        mock_llm = mock_all_external_apis['mock_llm']
        from langchain_core.messages import AIMessage
        mock_response = AIMessage(content="並行処理応答")
        mock_llm.invoke.return_value = mock_response
        
        with csrf_client.session_transaction() as sess:'''),
]

# 修正を適用
for pattern, replacement in fixes:
    content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)

# 残りの構文エラーを手動で修正
content = content.replace(
    '    def test_session_history_consistency(self, csrf_client):\n        """セッション履歴の一貫性を確認"""\n            # 各リクエストに異なる応答を設定',
    '''    def test_session_history_consistency(self, csrf_client, mock_all_external_apis):
        """セッション履歴の一貫性を確認"""
        # グローバルモックを使用
        mock_llm = mock_all_external_apis['mock_llm']
        
        # 各リクエストに異なる応答を設定'''
)

content = content.replace(
    '''    def test_graceful_degradation_on_service_unavailable(self, csrf_client):
        """サービス利用不可時の適切な劣化処理を確認"""
                sess['chat_settings'] = {''',
    '''    def test_graceful_degradation_on_service_unavailable(self, csrf_client, mock_all_external_apis):
        """サービス利用不可時の適切な劣化処理を確認"""
        # グローバルモックを使用
        mock_llm = mock_all_external_apis['mock_llm']
        from langchain_core.messages import AIMessage
        mock_llm.invoke.side_effect = Exception("サービス利用不可")
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {'''
)

# 他のモック参照を修正
content = content.replace(
    '''        mock_llm = MagicMock()
        from langchain_core.messages import AIMessage
        mock_response = AIMessage(content="メモリ効率テスト")
        mock_llm.invoke.return_value = mock_response''',
    '''        # グローバルモックを使用
        mock_llm = mock_all_external_apis['mock_llm']
        from langchain_core.messages import AIMessage
        mock_response = AIMessage(content="メモリ効率テスト")
        mock_llm.invoke.return_value = mock_response'''
)

content = content.replace(
    '''        mock_llm = MagicMock()
        
        # 成功、失敗、成功のパターンを設定''',
    '''        # グローバルモックを使用
        mock_llm = mock_all_external_apis['mock_llm']
        
        # 成功、失敗、成功のパターンを設定'''
)

# ファイルに書き戻し
with open('tests/test_app_integration_advanced.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("統合テストの構文エラーを修正しました。")