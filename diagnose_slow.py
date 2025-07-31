#!/usr/bin/env python3
"""
シナリオモードの遅延問題を診断するスクリプト
"""
import time
import psutil
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# メモリ使用量を表示
process = psutil.Process(os.getpid())
print(f"初期メモリ使用量: {process.memory_info().rss / 1024 / 1024:.2f} MB")

# データベース接続設定
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost/workplace_roleplay')

try:
    # データベース接続
    engine = create_engine(DATABASE_URL, echo=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("\n=== データベース診断開始 ===\n")
    
    # 1. テーブルサイズの確認
    print("1. テーブルサイズの確認:")
    tables = ['users', 'practice_sessions', 'conversation_logs', 'ai_personas', 'persona_memories']
    
    for table in tables:
        try:
            result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"   {table}: {count} 行")
        except Exception as e:
            print(f"   {table}: エラー - {e}")
    
    # 2. インデックスの確認
    print("\n2. インデックスの確認:")
    result = session.execute(text("""
        SELECT 
            schemaname,
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname;
    """))
    
    for row in result:
        print(f"   {row.tablename}.{row.indexname}")
    
    # 3. 実行中のクエリ確認
    print("\n3. 実行中のクエリ:")
    result = session.execute(text("""
        SELECT 
            pid,
            now() - pg_stat_activity.query_start AS duration,
            query,
            state
        FROM pg_stat_activity
        WHERE (now() - pg_stat_activity.query_start) > interval '1 second'
        AND state != 'idle'
        ORDER BY duration DESC;
    """))
    
    for row in result:
        print(f"   PID: {row.pid}, Duration: {row.duration}, State: {row.state}")
        print(f"   Query: {row.query[:100]}...")
    
    # 4. ペルソナ関連データの確認
    print("\n4. ペルソナ関連の重いクエリシミュレーション:")
    
    start_time = time.time()
    # N+1クエリの可能性をチェック
    from models import AIPersona, PersonaMemory, PracticeSession
    from database import init_database
    from app import app
    
    with app.app_context():
        # すべてのペルソナを取得（N+1の可能性）
        personas = session.query(AIPersona).all()
        print(f"   ペルソナ数: {len(personas)}")
        
        # 各ペルソナのメモリを個別に取得（N+1問題）
        for persona in personas[:3]:  # 最初の3つだけテスト
            memories = session.query(PersonaMemory).filter_by(persona_id=persona.id).all()
            print(f"   {persona.name}: {len(memories)} メモリ")
    
    elapsed = time.time() - start_time
    print(f"   実行時間: {elapsed:.2f} 秒")
    
    # 5. 最適化されたクエリ
    print("\n5. 最適化されたクエリ（joinedload使用）:")
    from sqlalchemy.orm import joinedload
    
    start_time = time.time()
    with app.app_context():
        # eager loadingで一度に取得
        personas_optimized = session.query(AIPersona).options(
            joinedload(AIPersona.memories)
        ).all()
        
        for persona in personas_optimized[:3]:
            print(f"   {persona.name}: {len(persona.memories)} メモリ（事前ロード済み）")
    
    elapsed = time.time() - start_time
    print(f"   実行時間: {elapsed:.2f} 秒")
    
    session.close()
    
except Exception as e:
    print(f"エラーが発生しました: {e}")
    import traceback
    traceback.print_exc()

# 最終メモリ使用量
print(f"\n最終メモリ使用量: {process.memory_info().rss / 1024 / 1024:.2f} MB")