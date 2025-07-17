"""
データベース設定と初期化

PostgreSQLとの接続管理、マイグレーション設定
"""
import os
from flask import Flask
from flask_migrate import Migrate
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from models import db
import logging

logger = logging.getLogger(__name__)
migrate = Migrate()


def get_database_uri():
    """データベースURIを環境変数から取得"""
    # 環境変数から各パラメータを取得
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'workplace_roleplay')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', '')
    
    # PostgreSQL URI を構築
    if db_password:
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    else:
        return f"postgresql://{db_user}@{db_host}:{db_port}/{db_name}"


def check_database_connection(uri):
    """データベース接続をテスト"""
    try:
        engine = create_engine(uri)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ データベース接続成功")
        return True
    except OperationalError as e:
        logger.error(f"❌ データベース接続失敗: {str(e)}")
        return False


def init_database(app: Flask):
    """データベースとマイグレーションを初期化"""
    # データベースURIを設定
    database_uri = get_database_uri()
    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # エコーモード（開発環境のみ）
    app.config['SQLALCHEMY_ECHO'] = os.getenv('FLASK_ENV') == 'development'
    
    # 接続プールの設定
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,  # 接続の健全性チェック
    }
    
    # データベース接続をテスト
    if not check_database_connection(database_uri):
        logger.warning("⚠️ データベース接続失敗。セッションベースモードで継続します。")
        # データベースが利用できない場合の処理
        app.config['DATABASE_AVAILABLE'] = False
        return False
    
    # SQLAlchemyとFlask-Migrateを初期化
    db.init_app(app)
    migrate.init_app(app, db)
    
    app.config['DATABASE_AVAILABLE'] = True
    logger.info("✅ データベース初期化完了")
    
    return True


def create_initial_data(app: Flask):
    """初期データを作成（シナリオ情報の同期など）"""
    from scenarios import load_scenarios
    from models import Scenario
    
    with app.app_context():
        try:
            # 既存のシナリオをチェック
            existing_scenarios = {s.yaml_id: s for s in Scenario.query.all()}
            
            # YAMLファイルからシナリオを読み込み
            yaml_scenarios = load_scenarios()
            
            # 新しいシナリオを追加
            added_count = 0
            for yaml_id, scenario_data in yaml_scenarios.items():
                if yaml_id not in existing_scenarios:
                    new_scenario = Scenario(
                        yaml_id=yaml_id,
                        title=scenario_data.get('title', ''),
                        summary=scenario_data.get('summary', ''),
                        difficulty=scenario_data.get('difficulty', ''),
                        category=scenario_data.get('tags', ['その他'])[0] if scenario_data.get('tags') else 'その他'
                    )
                    db.session.add(new_scenario)
                    added_count += 1
            
            if added_count > 0:
                db.session.commit()
                logger.info(f"✅ {added_count}個の新しいシナリオをデータベースに追加しました")
            else:
                logger.info("ℹ️ 新しいシナリオはありません")
                
        except Exception as e:
            logger.error(f"初期データ作成エラー: {str(e)}")
            db.session.rollback()


# データベースヘルパー関数
def get_or_create_scenario(yaml_id, scenario_data=None):
    """シナリオを取得または作成"""
    from models import Scenario
    
    scenario = Scenario.query.filter_by(yaml_id=yaml_id).first()
    if not scenario and scenario_data:
        scenario = Scenario(
            yaml_id=yaml_id,
            title=scenario_data.get('title', ''),
            summary=scenario_data.get('summary', ''),
            difficulty=scenario_data.get('difficulty', ''),
            category=scenario_data.get('tags', ['その他'])[0] if scenario_data.get('tags') else 'その他'
        )
        db.session.add(scenario)
        db.session.commit()
    
    return scenario


def create_practice_session(user_id, session_type, scenario_id=None, ai_model=None):
    """新しい練習セッションを作成"""
    from models import PracticeSession, SessionType
    
    session = PracticeSession(
        user_id=user_id,
        session_type=SessionType(session_type),
        scenario_id=scenario_id,
        ai_model=ai_model
    )
    db.session.add(session)
    db.session.commit()
    
    return session


def add_conversation_log(session_id, speaker, message, message_type='text'):
    """会話ログを追加"""
    from models import ConversationLog
    
    log = ConversationLog(
        session_id=session_id,
        speaker=speaker,
        message=message,
        message_type=message_type
    )
    db.session.add(log)
    db.session.commit()
    
    return log


def save_strength_analysis(session_id, analysis_result, feedback_text=None):
    """強み分析結果を保存"""
    from models import StrengthAnalysis
    
    # 既存の分析結果があれば更新、なければ新規作成
    analysis = StrengthAnalysis.query.filter_by(session_id=session_id).first()
    
    if not analysis:
        analysis = StrengthAnalysis(session_id=session_id)
    
    # スコアを更新
    analysis.empathy = analysis_result.get('empathy', 0.0)
    analysis.clarity = analysis_result.get('clarity', 0.0)
    analysis.listening = analysis_result.get('listening', 0.0)
    analysis.problem_solving = analysis_result.get('problem_solving', 0.0)
    analysis.assertiveness = analysis_result.get('assertiveness', 0.0)
    analysis.flexibility = analysis_result.get('flexibility', 0.0)
    
    # フィードバックと改善提案
    analysis.feedback_text = feedback_text
    analysis.overall_score = sum([
        analysis.empathy, analysis.clarity, analysis.listening,
        analysis.problem_solving, analysis.assertiveness, analysis.flexibility
    ]) / 6.0
    
    db.session.add(analysis)
    db.session.commit()
    
    return analysis