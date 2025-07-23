#!/usr/bin/env python3
"""
核心ファイルのカバレッジを迅速に測定するスクリプト
"""
import coverage
import subprocess
import os
import sys

def main():
    print("=== 核心ファイルのカバレッジ測定 ===")
    
    # カバレッジ測定を開始
    cov = coverage.Coverage(source=['app', 'services', 'auth'])
    cov.start()
    
    try:
        # 必要なモジュールをインポートして基本的な実行
        print("核心モジュールのインポートと基本実行...")
        
        # app.pyの実行
        try:
            import app
            print(f"✅ app.py インポート成功")
            
            # 基本関数の実行
            if hasattr(app, 'format_datetime'):
                result = app.format_datetime('2024-01-15T10:30:45')
                print(f"  format_datetime: {result}")
            
            if hasattr(app, 'get_available_gemini_models'):
                models = app.get_available_gemini_models()
                print(f"  available models: {len(models)} models")
                
        except Exception as e:
            print(f"❌ app.py エラー: {e}")
        
        # services.pyの実行
        try:
            import services
            print(f"✅ services.py インポート成功")
        except Exception as e:
            print(f"❌ services.py エラー: {e}")
        
        # auth.pyの実行
        try:
            import auth
            print(f"✅ auth.py インポート成功")
        except Exception as e:
            print(f"❌ auth.py エラー: {e}")
        
    finally:
        # カバレッジ測定を停止
        cov.stop()
        cov.save()
        
        # レポート生成
        print("\n=== カバレッジレポート ===")
        
        # コンソールレポート
        cov.report(show_missing=True)
        
        # HTMLレポート生成
        try:
            cov.html_report(directory='htmlcov_quick')
            print(f"\n✅ HTMLレポートを htmlcov_quick/ に生成しました")
        except Exception as e:
            print(f"❌ HTMLレポート生成エラー: {e}")
        
        # 各ファイルの詳細カバレッジ
        print("\n=== 詳細カバレッジ分析 ===")
        
        for filename in ['app.py', 'services.py', 'auth.py']:
            if os.path.exists(filename):
                try:
                    analysis = cov.analysis2(filename)
                    executed_lines = len(analysis[1])
                    missing_lines = len(analysis[3])
                    total_lines = executed_lines + missing_lines
                    coverage_percent = (executed_lines / total_lines * 100) if total_lines > 0 else 0
                    
                    print(f"\n📁 {filename}:")
                    print(f"  総行数: {total_lines}")
                    print(f"  実行済み: {executed_lines}")
                    print(f"  未実行: {missing_lines}")
                    print(f"  カバレッジ: {coverage_percent:.1f}%")
                    
                    if missing_lines > 0:
                        print(f"  未実行行: {list(analysis[3])[:10]}{'...' if len(analysis[3]) > 10 else ''}")
                        
                except Exception as e:
                    print(f"❌ {filename} 分析エラー: {e}")

if __name__ == "__main__":
    main()