#!/usr/bin/env python3
"""
開発環境の動作確認スクリプト
仮想環境が正しく設定されているかを確認します
"""

import sys
import os
from pathlib import Path


def check_virtual_env():
    """仮想環境の確認"""
    print("🔍 仮想環境の確認...")

    # Python実行可能ファイルのパス確認
    python_path = sys.executable
    project_root = Path(__file__).parent
    expected_venv_path = project_root / "venv" / "bin" / "python"

    if str(expected_venv_path) in python_path:
        print(f"✅ 仮想環境を使用: {python_path}")
        return True
    else:
        print(f"❌ 仮想環境未使用: {python_path}")
        print(f"   期待されるパス: {expected_venv_path}")
        return False


def check_required_packages():
    """必要なパッケージの確認"""
    print("\n📦 パッケージの確認...")

    required_packages = [
        "flask",
        "pytest",
        "black",
        "flake8",
        "isort",
        "mypy",
        "google.generativeai",
        "langchain",
        "redis",
    ]

    missing_packages = []

    for package in required_packages:
        try:
            if package == "google.generativeai":
                import google.generativeai as genai

                print(f"✅ {package}: {genai.__version__}")
            elif package == "langchain":
                import langchain

                # langchainはバージョン取得方法が特殊
                print(f"✅ {package}: インポート成功")
            else:
                module = __import__(package)
                version = getattr(module, "__version__", "バージョン不明")
                print(f"✅ {package}: {version}")
        except ImportError:
            print(f"❌ {package}: インストールされていません")
            missing_packages.append(package)

    return len(missing_packages) == 0


def check_project_structure():
    """プロジェクト構造の確認"""
    print("\n🏗️ プロジェクト構造の確認...")

    required_files = [
        "app.py",
        "requirements.txt",
        "requirements-dev.txt",
        ".env.example",
        "examples/csp_usage_example.py",
        "tests/test_xss_vulnerabilities.py",
    ]

    project_root = Path(__file__).parent
    missing_files = []

    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}: ファイルが見つかりません")
            missing_files.append(file_path)

    return len(missing_files) == 0


def check_import_functionality():
    """重要なモジュールのインポート確認"""
    print("\n🔧 機能モジュールの確認...")

    try:
        # アプリケーションのメイン機能
        print("  App モジュール...")
        import app

        print("  ✅ app.py インポート成功")

        # テストモジュール
        print("  テストモジュール...")
        import tests.test_xss_vulnerabilities

        print("  ✅ test_xss_vulnerabilities.py インポート成功")

        # CSP使用例
        print("  CSP使用例...")
        import examples.csp_usage_example

        print("  ✅ csp_usage_example.py インポート成功")

        return True

    except Exception as e:
        print(f"  ❌ インポートエラー: {e}")
        return False


def main():
    """メイン実行関数"""
    print("🚀 開発環境の動作確認を開始...")
    print("=" * 50)

    checks = [
        ("仮想環境", check_virtual_env),
        ("必要パッケージ", check_required_packages),
        ("プロジェクト構造", check_project_structure),
        ("機能モジュール", check_import_functionality),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name}の確認中にエラー: {e}")
            results.append((name, False))

    print("\n" + "=" * 50)
    print("📊 確認結果サマリー:")

    all_passed = True
    for name, passed in results:
        status = "✅ 成功" if passed else "❌ 失敗"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 すべての確認が成功しました！")
        print("\n💡 次のステップ:")
        print("  1. IDEでPythonインタープリターを設定:")
        print(f"     {Path(__file__).parent / 'venv' / 'bin' / 'python'}")
        print("  2. アプリケーションを起動: python app.py")
        print("  3. テストを実行: pytest")
    else:
        print("⚠️  一部の確認で問題が見つかりました。")
        print("    上記のエラーを確認してください。")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
