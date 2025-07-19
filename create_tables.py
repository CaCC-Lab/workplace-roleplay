"""
データベーステーブルを直接作成するスクリプト
PostgreSQLの権限問題を回避するための一時的な解決策
"""

import os
from app import app
from database import db
from models import *
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_all_tables():
    """すべてのテーブルを作成"""
    with app.app_context():
        try:
            # DifficultyLevelのEnum型を作成
            logger.info("Creating enum types...")
            db.session.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE difficulty_level_enum AS ENUM ('初級', '中級', '上級', '不明');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            db.session.commit()
            
            # すべてのテーブルを作成
            logger.info("Creating all tables...")
            db.create_all()
            
            logger.info("✅ All tables created successfully!")
            
            # 初期アチーブメントデータを作成
            create_initial_achievements()
            
        except Exception as e:
            logger.error(f"❌ Error creating tables: {e}")
            db.session.rollback()
            raise

def create_initial_achievements():
    """初期アチーブメントデータを作成"""
    try:
        # 既存のアチーブメントをチェック
        existing_count = Achievement.query.count()
        if existing_count > 0:
            logger.info(f"ℹ️  既に {existing_count} 個のアチーブメントが存在します")
            return
        
        logger.info("Creating initial achievements...")
        
        achievements = [
            # 練習回数系
            {
                'name': '初めての一歩',
                'description': '初めて練習を完了しました！',
                'icon': '🎯',
                'category': 'practice',
                'threshold_type': 'count',
                'threshold_value': 1,
                'points': 10
            },
            {
                'name': '練習の習慣化',
                'description': '10回練習を完了しました',
                'icon': '📚',
                'category': 'practice',
                'threshold_type': 'count',
                'threshold_value': 10,
                'points': 30
            },
            {
                'name': 'コミュニケーションマスター',
                'description': '50回練習を完了しました',
                'icon': '🏆',
                'category': 'practice',
                'threshold_type': 'count',
                'threshold_value': 50,
                'points': 100
            },
            # 連続練習系
            {
                'name': '継続は力なり',
                'description': '3日連続で練習しました',
                'icon': '🔥',
                'category': 'consistency',
                'threshold_type': 'streak',
                'threshold_value': 3,
                'points': 20
            },
            {
                'name': '週間チャンピオン',
                'description': '7日連続で練習しました',
                'icon': '⭐',
                'category': 'consistency',
                'threshold_type': 'streak',
                'threshold_value': 7,
                'points': 50
            },
            # スキル向上系
            {
                'name': '共感力の向上',
                'description': '共感力スコアが0.8以上を達成',
                'icon': '💝',
                'category': 'skill',
                'threshold_type': 'score',
                'threshold_value': 80,  # 0.8 * 100
                'points': 40
            },
            {
                'name': '明確な伝達者',
                'description': '明確性スコアが0.8以上を達成',
                'icon': '💬',
                'category': 'skill',
                'threshold_type': 'score',
                'threshold_value': 80,
                'points': 40
            },
            {
                'name': '優れた聞き手',
                'description': '傾聴力スコアが0.8以上を達成',
                'icon': '👂',
                'category': 'skill',
                'threshold_type': 'score',
                'threshold_value': 80,
                'points': 40
            },
            # 特別なアチーブメント
            {
                'name': '早起きは三文の徳',
                'description': '朝6時から9時の間に練習しました',
                'icon': '🌅',
                'category': 'special',
                'threshold_type': 'custom',
                'threshold_value': 1,
                'points': 15
            },
            {
                'name': '夜の学習者',
                'description': '夜9時以降に練習しました',
                'icon': '🌙',
                'category': 'special',
                'threshold_type': 'custom',
                'threshold_value': 1,
                'points': 15
            },
            {
                'name': '週末戦士',
                'description': '土日に練習しました',
                'icon': '🎉',
                'category': 'special',
                'threshold_type': 'custom',
                'threshold_value': 1,
                'points': 15
            },
            {
                'name': '多様な経験',
                'description': '5種類以上の異なるシナリオを練習',
                'icon': '🎭',
                'category': 'special',
                'threshold_type': 'custom',
                'threshold_value': 5,
                'points': 30
            }
        ]
        
        for achievement_data in achievements:
            achievement = Achievement(**achievement_data)
            db.session.add(achievement)
        
        db.session.commit()
        logger.info(f"✅ Created {len(achievements)} initial achievements!")
        
    except Exception as e:
        logger.error(f"❌ Error creating achievements: {e}")
        db.session.rollback()
        raise

if __name__ == "__main__":
    logger.info("Starting database table creation...")
    create_all_tables()