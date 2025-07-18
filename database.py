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


def get_safe_database_uri():
    """ログ出力用にパスワードをマスクしたデータベースURIを取得"""
    # 環境変数から各パラメータを取得
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'workplace_roleplay')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', '')
    
    # パスワードをマスクしたURI を構築
    if db_password:
        return f"postgresql://{db_user}:***@{db_host}:{db_port}/{db_name}"
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
    with app.app_context():
        try:
            # シナリオデータをYAMLファイルから読み込んで同期
            sync_scenarios_from_yaml()
            logger.info("✅ 初期データの作成が完了しました")
        except Exception as e:
            logger.error(f"初期データ作成エラー: {str(e)}")
            db.session.rollback()


def sync_scenarios_from_yaml():
    """
    scenarios/data/ ディレクトリ内のYAMLファイルからシナリオを読み込み、
    データベースと同期する。
    - 既存のシナリオは更新
    - 新しいシナリオは追加
    """
    import yaml
    from models import Scenario, DifficultyLevel
    
    scenario_dir = os.path.join(os.path.dirname(__file__), 'scenarios', 'data')
    if not os.path.isdir(scenario_dir):
        logger.warning(f"Warning: Scenario directory not found at {scenario_dir}")
        return

    updated_count = 0
    added_count = 0
    
    for filename in os.listdir(scenario_dir):
        if filename.endswith('.yaml') or filename.endswith('.yml'):
            filepath = os.path.join(scenario_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)

                yaml_id = data.get('id')
                if not yaml_id:
                    continue

                # difficultyをEnumに変換。存在しない場合は UNKNOWN
                difficulty_str = data.get('difficulty', '不明')
                try:
                    difficulty_enum = DifficultyLevel(difficulty_str)
                except ValueError:
                    difficulty_enum = DifficultyLevel.UNKNOWN

                # カテゴリを抽出
                category = _extract_category(data)

                # データベースで既存のシナリオを検索
                scenario = Scenario.query.filter_by(yaml_id=yaml_id).first()

                if scenario:
                    # 既存シナリオの更新
                    scenario.title = data.get('title', '')
                    scenario.summary = data.get('summary', '')
                    scenario.difficulty = difficulty_enum
                    scenario.category = category
                    updated_count += 1
                else:
                    # 新規シナリオの作成
                    scenario = Scenario(
                        yaml_id=yaml_id,
                        title=data.get('title', ''),
                        summary=data.get('summary', ''),
                        difficulty=difficulty_enum,
                        category=category
                    )
                    db.session.add(scenario)
                    added_count += 1

            except Exception as e:
                logger.warning(f"Warning: Error processing {filename}: {e}")
                continue

    if updated_count > 0 or added_count > 0:
        db.session.commit()
        logger.info(f"✅ シナリオの同期が完了しました (追加: {added_count}, 更新: {updated_count})")
    else:
        logger.info("ℹ️ 同期対象のシナリオはありませんでした")


def _extract_category(scenario_data):
    """シナリオデータからカテゴリを抽出する"""
    tags = scenario_data.get('tags', [])
    return tags[0] if tags else 'その他'


# ========== 非推奨関数（services.pyに移行済み） ==========
# これらの関数は services.py のサービスレイヤーに移行されました。
# 新しいコードでは services.py の対応する関数を使用してください。

# DEPRECATED: 代わりに ScenarioService.get_by_yaml_id() と ScenarioService.sync_from_yaml() を使用
def get_or_create_scenario(yaml_id, scenario_data=None):
    """
    【非推奨】シナリオを取得または作成
    
    移行先:
    - ScenarioService.get_by_yaml_id(yaml_id)
    - ScenarioService.sync_from_yaml() (一括同期の場合)
    """
    import warnings
    warnings.warn(
        "get_or_create_scenario() は非推奨です。services.ScenarioService を使用してください。",
        DeprecationWarning,
        stacklevel=2
    )
    
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


# DEPRECATED: 代わりに SessionService.create_session() を使用
def create_practice_session(user_id, session_type, scenario_id=None, ai_model=None):
    """
    【非推奨】新しい練習セッションを作成
    
    移行先: SessionService.create_session()
    """
    import warnings
    warnings.warn(
        "create_practice_session() は非推奨です。services.SessionService.create_session() を使用してください。",
        DeprecationWarning,
        stacklevel=2
    )
    
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


# DEPRECATED: 代わりに ConversationService.add_log() を使用
def add_conversation_log(session_id, speaker, message, message_type='text'):
    """
    【非推奨】会話ログを追加
    
    移行先: ConversationService.add_log()
    """
    import warnings
    warnings.warn(
        "add_conversation_log() は非推奨です。services.ConversationService.add_log() を使用してください。",
        DeprecationWarning,
        stacklevel=2
    )
    
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
    
    # バリデーション実行
    try:
        analysis.validate_skill_scores()
    except ValueError as e:
        logger.error(f"スキルスコアのバリデーションエラー: {e}")
        raise
    
    db.session.add(analysis)
    db.session.commit()
    
    return analysis