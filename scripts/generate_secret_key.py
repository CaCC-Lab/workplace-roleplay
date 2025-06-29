#!/usr/bin/env python3
"""
セキュアなシークレットキーを生成するスクリプト

使用方法:
    python scripts/generate_secret_key.py
    python scripts/generate_secret_key.py --length 48
    python scripts/generate_secret_key.py --check "existing-key-to-check"
"""
import sys
import os
import argparse

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.security_utils import (
    generate_secure_secret_key,
    is_secure_secret_key,
    recommend_secret_key_improvements
)


def main():
    parser = argparse.ArgumentParser(
        description="Generate or check secure secret keys for Flask applications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Generate a 64-character key (default):
    python generate_secret_key.py
    
  Generate a 48-character key:
    python generate_secret_key.py --length 48
    
  Check if a key is secure:
    python generate_secret_key.py --check "your-existing-key"
    
  Generate multiple keys:
    python generate_secret_key.py --count 3
"""
    )
    
    parser.add_argument(
        "-l", "--length",
        type=int,
        default=64,
        help="Key length in characters (default: 64, minimum: 32)"
    )
    
    parser.add_argument(
        "-c", "--check",
        type=str,
        help="Check if the provided key is secure"
    )
    
    parser.add_argument(
        "-n", "--count",
        type=int,
        default=1,
        help="Number of keys to generate (default: 1)"
    )
    
    parser.add_argument(
        "--env-format",
        action="store_true",
        help="Output in .env file format"
    )
    
    args = parser.parse_args()
    
    # キーのチェックモード
    if args.check:
        print("Checking secret key security...\n")
        is_secure, message = is_secure_secret_key(args.check)
        
        if is_secure:
            print("✅ Your secret key is secure!")
            print(f"   Length: {len(args.check)} characters")
        else:
            print("❌ Your secret key has security issues!")
            print(f"\n{recommend_secret_key_improvements(args.check)}")
        
        sys.exit(0 if is_secure else 1)
    
    # キー生成モード
    if args.length < 32:
        print("⚠️  Warning: Minimum recommended length is 32 characters")
        print(f"   Generating {args.length}-character key anyway...\n")
    
    print(f"Generating {args.count} secure secret key(s) ({args.length} characters each):\n")
    
    for i in range(args.count):
        key = generate_secure_secret_key(args.length)
        
        if args.env_format:
            print(f"FLASK_SECRET_KEY={key}")
        else:
            if args.count > 1:
                print(f"Key {i + 1}:")
            print(key)
            
            if i == 0:  # 最初のキーのみ詳細情報を表示
                print(f"\nKey details:")
                print(f"  Length: {len(key)} characters")
                print(f"  Unique characters: {len(set(key))}")
                is_secure, _ = is_secure_secret_key(key)
                print(f"  Security check: {'✅ Passed' if is_secure else '❌ Failed'}")
                
                if not args.env_format:
                    print(f"\nTo use this key, add to your .env file:")
                    print(f"FLASK_SECRET_KEY={key}")
        
        if args.count > 1 and i < args.count - 1:
            print()  # 複数キー生成時の区切り


if __name__ == "__main__":
    main()