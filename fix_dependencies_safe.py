#!/usr/bin/env python3
"""
依存関係の問題を修正するスクリプト（安全版）
メインアプリを動作可能な状態に戻す
"""

import sys
import os
import json
import tempfile
from typing import List, Dict, Tuple, Optional
import importlib.metadata
import importlib.util

def is_package_installed(package_name: str) -> bool:
    """パッケージがインストールされているか確認"""
    try:
        importlib.metadata.version(package_name)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False

def get_installed_packages() -> Dict[str, str]:
    """インストール済みパッケージのリストを取得"""
    packages = {}
    for dist in importlib.metadata.distributions():
        if dist.name:
            packages[dist.name.lower()] = dist.version
    return packages

def create_requirements_file(packages: List[str], filename: str) -> None:
    """requirements.txtファイルを作成"""
    with open(filename, 'w', encoding='utf-8') as f:
        for package in packages:
            f.write(f"{package}\n")

def validate_package_spec(package_spec: str) -> Tuple[bool, str]:
    """パッケージ指定の妥当性を検証"""
    # 基本的な検証: パッケージ名に危険な文字が含まれていないか
    dangerous_chars = [';', '&', '|', '>', '<', '`', '$', '(', ')', '{', '}']
    for char in dangerous_chars:
        if char in package_spec:
            return False, f"危険な文字 '{char}' が含まれています"
    
    # パッケージ指定の形式を確認
    if '==' in package_spec:
        name, version = package_spec.split('==', 1)
        # バージョン番号の基本的な検証
        if not version.replace('.', '').replace('-', '').replace('_', '').isalnum():
            return False, "不正なバージョン番号形式"
    elif package_spec.strip() != package_spec:
        return False, "パッケージ名に不要な空白が含まれています"
    
    return True, "OK"

def fix_dependencies():
    """依存関係を修正"""
    
    print("=== 依存関係の修正を開始（安全版） ===")
    
    # 現在のインストール状況を確認
    print("\n現在のパッケージ状況を確認中...")
    installed_packages = get_installed_packages()
    
    # 1. 問題のあるパッケージを確認
    print("\n1. 問題のあるパッケージを確認...")
    packages_to_remove = [
        "langchain",
        "langchain-core", 
        "langchain-community",
        "langchain-openai",
        "langchain-google-genai",
        "pydantic",
        "pydantic-core",
        "pydantic-settings"
    ]
    
    found_problematic = []
    for package in packages_to_remove:
        if package.lower() in installed_packages:
            version = installed_packages[package.lower()]
            print(f"  ⚠️  {package} ({version}) がインストールされています")
            found_problematic.append(package)
        else:
            print(f"  ✓ {package} はインストールされていません")
    
    if found_problematic:
        print(f"\n⚠️  {len(found_problematic)} 個の問題のあるパッケージが見つかりました")
        print("これらのパッケージは手動でアンインストールする必要があります:")
        print("```")
        for package in found_problematic:
            print(f"pip uninstall -y {package}")
        print("```")
    
    # 2. 互換性のあるバージョンのインストールを推奨
    print("\n2. 互換性のあるバージョンのインストールを推奨...")
    compatible_packages = [
        "pydantic==2.5.0",
        "pydantic-settings==2.1.0",
        "google-generativeai==0.3.2",
        "langchain==0.1.9",
        "langchain-community==0.0.24",
        "langchain-google-genai==0.0.9",
        "werkzeug==2.3.7"
    ]
    
    # パッケージ指定の検証
    valid_packages = []
    for package in compatible_packages:
        is_valid, message = validate_package_spec(package)
        if is_valid:
            valid_packages.append(package)
        else:
            print(f"  ⚠️  {package} - 検証エラー: {message}")
    
    # requirements_fix.txtを作成
    requirements_file = "requirements_fix.txt"
    create_requirements_file(valid_packages, requirements_file)
    
    print(f"\n✅ {requirements_file} を作成しました")
    print("\n以下のコマンドを実行して依存関係を修正してください:")
    print("```")
    if found_problematic:
        print("# 1. 問題のあるパッケージをアンインストール")
        for package in found_problematic:
            print(f"pip uninstall -y {package}")
        print()
    print("# 2. 互換性のあるバージョンをインストール")
    print(f"pip install -r {requirements_file}")
    print("```")
    
    # 現在の環境情報を表示
    print("\n=== 環境情報 ===")
    print(f"Python バージョン: {sys.version}")
    print(f"実行パス: {sys.executable}")
    
    # 重要なパッケージの現在のバージョンを表示
    important_packages = ["flask", "google-generativeai", "pydantic", "langchain"]
    print("\n重要なパッケージの現在のバージョン:")
    for package in important_packages:
        if package.lower() in installed_packages:
            version = installed_packages[package.lower()]
            print(f"  {package}: {version}")
        else:
            print(f"  {package}: 未インストール")
    
    print("\n=== 依存関係の修正手順完了 ===")

if __name__ == "__main__":
    fix_dependencies()