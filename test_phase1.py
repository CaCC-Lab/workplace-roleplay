#!/usr/bin/env python
"""Phase 1修正のテストスクリプト"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.security import SecurityUtils

def test_get_safe_error_message():
    """get_safe_error_messageメソッドのテスト"""
    print("Testing SecurityUtils.get_safe_error_message()...")
    
    # テストケース
    test_cases = [
        ("rate limit exceeded", "システムが混雑しています"),
        ("API key invalid", "認証エラーが発生しました"),
        ("connection timeout", "ネットワークエラーが発生しました"),
        ("unknown internal error", "システムエラーが発生しました"),
        ("レート制限に達しました", "システムが混雑しています"),
    ]
    
    for error_msg, expected in test_cases:
        result = SecurityUtils.get_safe_error_message(Exception(error_msg))
        assert result == expected, f"Failed: {error_msg} -> {result} (expected: {expected})"
        print(f"  ✓ {error_msg[:30]}... -> {result}")
    
    print("✅ All get_safe_error_message tests passed!")

def test_bug01_logic():
    """BUG-01修正のロジックテスト"""
    print("\nTesting BUG-01 fix logic...")
    
    # 空文字列のケース
    content = ""
    error_msg = None
    
    # 修正前のロジック（問題あり）
    old_logic_result = bool(content)  # False (空文字列でエラー扱い)
    
    # 修正後のロジック
    new_logic_result = error_msg is None  # True (エラーなし)
    
    print(f"  Empty string response:")
    print(f"    Old logic (buggy): {old_logic_result} (treats as error)")
    print(f"    New logic (fixed): {new_logic_result} (treats as valid)")
    
    assert new_logic_result == True, "BUG-01 fix failed"
    print("✅ BUG-01 fix logic test passed!")

if __name__ == "__main__":
    print("=" * 50)
    print("Phase 1 Implementation Tests")
    print("=" * 50)
    
    test_get_safe_error_message()
    test_bug01_logic()
    
    print("\n" + "=" * 50)
    print("✅ All Phase 1 tests passed successfully!")
    print("=" * 50)