#!/usr/bin/env python3
"""
プロジェクトクリーンアップスクリプト
不要なファイル、デバッグコード、重複コードを削除
"""
import os
import shutil
import glob
import re
from typing import List, Set, Tuple
from datetime import datetime


class ProjectCleaner:
    """プロジェクトクリーンアップクラス"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.cleanup_report = {
            "cache_files": [],
            "debug_files": [],
            "backup_files": [],
            "temp_files": [],
            "unused_imports": [],
            "duplicate_files": [],
            "large_files": []
        }
        self.protected_patterns = [
            "venv/", "env/", ".git/", "__pycache__/",
            "node_modules/", ".pytest_cache/", ".mypy_cache/"
        ]
    
    def is_protected(self, path: str) -> bool:
        """保護されたパスかどうかチェック"""
        for pattern in self.protected_patterns:
            if pattern in path:
                return True
        return False
    
    def cleanup_cache_files(self):
        """キャッシュファイルを削除"""
        print("🧹 キャッシュファイルのクリーンアップ...")
        
        patterns = [
            "**/*.pyc",
            "**/__pycache__",
            "**/.DS_Store",
            "**/*.log",
            "**/*.tmp",
            "**/flask_session/*"
        ]
        
        for pattern in patterns:
            for file_path in glob.glob(pattern, recursive=True):
                if self.is_protected(file_path):
                    continue
                    
                self.cleanup_report["cache_files"].append(file_path)
                if not self.dry_run:
                    try:
                        if os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                        else:
                            os.remove(file_path)
                        print(f"  ✅ 削除: {file_path}")
                    except Exception as e:
                        print(f"  ❌ エラー: {file_path} - {e}")
                else:
                    print(f"  🔍 発見: {file_path}")
    
    def cleanup_debug_files(self):
        """デバッグ・テストファイルを整理"""
        print("\n🐛 デバッグファイルのクリーンアップ...")
        
        patterns = [
            "debug_*.py",
            "test_*.py",
            "debug_*.html",
            "test_*.html",
            "*_debug.*"
        ]
        
        # tests/ディレクトリ内のファイルは除外
        for pattern in patterns:
            for file_path in glob.glob(pattern):
                if "tests/" in file_path or self.is_protected(file_path):
                    continue
                
                self.cleanup_report["debug_files"].append(file_path)
                if not self.dry_run:
                    try:
                        os.remove(file_path)
                        print(f"  ✅ 削除: {file_path}")
                    except Exception as e:
                        print(f"  ❌ エラー: {file_path} - {e}")
                else:
                    print(f"  🔍 発見: {file_path}")
    
    def cleanup_backup_files(self):
        """バックアップファイルを整理"""
        print("\n💾 バックアップファイルのクリーンアップ...")
        
        patterns = [
            "*_backup_*.py",
            "*_old.py",
            "*_copy.py",
            "*.bak",
            "*~"
        ]
        
        for pattern in patterns:
            for file_path in glob.glob(pattern, recursive=True):
                if self.is_protected(file_path):
                    continue
                    
                self.cleanup_report["backup_files"].append(file_path)
                if not self.dry_run:
                    try:
                        os.remove(file_path)
                        print(f"  ✅ 削除: {file_path}")
                    except Exception as e:
                        print(f"  ❌ エラー: {file_path} - {e}")
                else:
                    print(f"  🔍 発見: {file_path}")
    
    def find_unused_imports(self):
        """未使用のインポートを検出"""
        print("\n📦 未使用インポートの検出...")
        
        py_files = glob.glob("**/*.py", recursive=True)
        
        for file_path in py_files:
            if self.is_protected(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 簡易的なインポート検出
                imports = re.findall(r'^(?:from\s+[\w.]+\s+)?import\s+(.+)$', content, re.MULTILINE)
                
                for imp in imports:
                    # インポートされた名前を抽出
                    names = re.findall(r'\w+', imp)
                    for name in names:
                        # コード内で使用されているかチェック
                        if name not in ['as', 'from'] and content.count(name) == 1:
                            self.cleanup_report["unused_imports"].append(f"{file_path}: {name}")
                            print(f"  🔍 未使用: {file_path} - {name}")
            except Exception as e:
                print(f"  ❌ エラー: {file_path} - {e}")
    
    def find_large_files(self, size_mb: int = 10):
        """大きなファイルを検出"""
        print(f"\n📏 {size_mb}MB以上のファイルを検出...")
        
        for root, dirs, files in os.walk("."):
            # 保護されたディレクトリをスキップ
            dirs[:] = [d for d in dirs if not any(p.rstrip('/') in os.path.join(root, d) for p in self.protected_patterns)]
            
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path)
                    if size > size_mb * 1024 * 1024:
                        size_mb_actual = size / (1024 * 1024)
                        self.cleanup_report["large_files"].append((file_path, size_mb_actual))
                        print(f"  🔍 大きなファイル: {file_path} ({size_mb_actual:.1f}MB)")
                except Exception as e:
                    pass
    
    def generate_gitignore_additions(self):
        """追加すべき.gitignoreエントリを提案"""
        print("\n📝 .gitignoreに追加すべきパターン...")
        
        patterns = set()
        
        # クリーンアップレポートから提案を生成
        for debug_file in self.cleanup_report["debug_files"]:
            if debug_file.startswith("debug_"):
                patterns.add("debug_*.py")
            if debug_file.startswith("test_") and "tests/" not in debug_file:
                patterns.add("test_*.py")
        
        for cache_file in self.cleanup_report["cache_files"]:
            if cache_file.endswith(".log"):
                patterns.add("*.log")
            if "flask_session" in cache_file:
                patterns.add("flask_session/")
        
        if patterns:
            print("\n# 追加推奨パターン:")
            for pattern in sorted(patterns):
                print(f"{pattern}")
    
    def generate_report(self):
        """クリーンアップレポートを生成"""
        print("\n" + "=" * 60)
        print("📊 クリーンアップサマリー")
        print("=" * 60)
        
        total_files = 0
        
        for category, files in self.cleanup_report.items():
            if category == "large_files":
                count = len(files)
                if count > 0:
                    total_size = sum(size for _, size in files)
                    print(f"{category}: {count}個 (合計 {total_size:.1f}MB)")
                    total_files += count
            else:
                count = len(files)
                if count > 0:
                    print(f"{category}: {count}個")
                    total_files += count
        
        print(f"\n合計: {total_files}個のファイル/問題を検出")
        
        if self.dry_run:
            print("\n⚠️  ドライランモードで実行されました。実際には何も削除されていません。")
            print("実際にクリーンアップを実行するには --execute フラグを使用してください。")
    
    def cleanup_duplicates(self):
        """重複ファイルを検出"""
        print("\n🔄 重複ファイルの検出...")
        
        # よくある重複パターン
        duplicate_patterns = [
            ("app.py", "app_*.py"),
            ("config.py", "config_*.py"),
        ]
        
        for original, pattern in duplicate_patterns:
            if os.path.exists(original):
                for dup in glob.glob(pattern):
                    if dup != original:
                        self.cleanup_report["duplicate_files"].append(dup)
                        print(f"  🔍 重複の可能性: {dup} (オリジナル: {original})")
    
    def run(self):
        """クリーンアップを実行"""
        print(f"🚀 プロジェクトクリーンアップを開始します...")
        print(f"モード: {'ドライラン' if self.dry_run else '実行'}")
        print("=" * 60)
        
        self.cleanup_cache_files()
        self.cleanup_debug_files()
        self.cleanup_backup_files()
        self.cleanup_duplicates()
        self.find_unused_imports()
        self.find_large_files()
        
        self.generate_report()
        self.generate_gitignore_additions()
        
        # レポートを保存
        if not self.dry_run:
            report_path = f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"クリーンアップレポート\n")
                f.write(f"実行日時: {datetime.now()}\n")
                f.write("=" * 60 + "\n")
                for category, files in self.cleanup_report.items():
                    f.write(f"\n{category}:\n")
                    for file in files:
                        f.write(f"  - {file}\n")
            print(f"\n📄 レポートを {report_path} に保存しました")


def main():
    import sys
    
    # コマンドライン引数をチェック
    dry_run = "--execute" not in sys.argv
    
    cleaner = ProjectCleaner(dry_run=dry_run)
    cleaner.run()


if __name__ == "__main__":
    main()