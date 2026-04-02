"""
Routes module for workplace-roleplay application.
Handles Blueprint registration and route management.
"""

from flask import Flask


def register_blueprints(app: Flask):
    """
    すべてのBlueprintをFlaskアプリケーションに登録

    Args:
        app: Flaskアプリケーションインスタンス
    """
    # 既存のA/Bテストルート
    try:
        from routes.ab_test_routes import ab_test_bp

        app.register_blueprint(ab_test_bp)
        print("✅ A/Bテストエンドポイントを登録しました (/api/v2/*)")
    except ImportError as e:
        print(f"⚠️ A/Bテストエンドポイントは利用できません: {e}")

    # メインルート（ホーム、ヘルスチェック等）
    try:
        from routes.main_routes import main_bp

        app.register_blueprint(main_bp)
        print("✅ メインルートを登録しました")
    except ImportError as e:
        print(f"⚠️ メインルートは利用できません: {e}")

    # チャットルート
    try:
        from routes.chat_routes import chat_bp

        app.register_blueprint(chat_bp)
        print("✅ チャットルートを登録しました")
    except ImportError as e:
        print(f"⚠️ チャットルートは利用できません: {e}")

    # シナリオルート
    try:
        from routes.scenario_routes import scenario_bp

        app.register_blueprint(scenario_bp)
        print("✅ シナリオルートを登録しました")
    except ImportError as e:
        print(f"⚠️ シナリオルートは利用できません: {e}")

    # 観戦モードルート
    try:
        from routes.watch_routes import watch_bp

        app.register_blueprint(watch_bp)
        print("✅ 観戦モードルートを登録しました")
    except ImportError as e:
        print(f"⚠️ 観戦モードルートは利用できません: {e}")

    # モデル関連ルート
    try:
        from routes.model_routes import model_bp

        app.register_blueprint(model_bp)
        print("✅ モデルルートを登録しました")
    except ImportError as e:
        print(f"⚠️ モデルルートは利用できません: {e}")

    # セッション管理ルート
    try:
        from routes.session_routes import session_bp

        app.register_blueprint(session_bp)
        print("✅ セッションルートを登録しました")
    except ImportError as e:
        print(f"⚠️ セッションルートは利用できません: {e}")

    # 強み分析ルート
    try:
        from routes.strength_routes import strength_bp

        app.register_blueprint(strength_bp)
        print("✅ 強み分析ルートを登録しました")
    except ImportError as e:
        print(f"⚠️ 強み分析ルートは利用できません: {e}")

    # TTSルート
    try:
        from routes.tts_routes import tts_bp

        app.register_blueprint(tts_bp)
        print("✅ TTSルートを登録しました")
    except ImportError as e:
        print(f"⚠️ TTSルートは利用できません: {e}")

    # 学習履歴ルート
    try:
        from routes.journal_routes import journal_bp

        app.register_blueprint(journal_bp)
        print("✅ 学習履歴ルートを登録しました")
    except ImportError as e:
        print(f"⚠️ 学習履歴ルートは利用できません: {e}")

    # 画像生成ルート
    try:
        from routes.image_routes import image_bp

        app.register_blueprint(image_bp)
        print("✅ 画像生成ルートを登録しました")
    except ImportError as e:
        print(f"⚠️ 画像生成ルートは利用できません: {e}")

    # APIドキュメントルート
    try:
        from routes.docs_routes import docs_bp, init_swagger

        app.register_blueprint(docs_bp)
        init_swagger(app)
        print("✅ APIドキュメントルートを登録しました (/api/docs/)")
    except ImportError as e:
        print(f"⚠️ APIドキュメントルートは利用できません: {e}")

    # ゲーミフィケーションルート
    try:
        from routes.gamification_routes import gamification_bp

        app.register_blueprint(gamification_bp)
        print("✅ ゲーミフィケーションルートを登録しました (/api/gamification/*)")
    except ImportError as e:
        print(f"⚠️ ゲーミフィケーションルートは利用できません: {e}")

    # 観戦クイズルート
    try:
        from routes.quiz_routes import quiz_bp

        app.register_blueprint(quiz_bp)
        print("✅ 観戦クイズルートを登録しました (/api/quiz/*)")
    except ImportError as e:
        print(f"⚠️ 観戦クイズルートは利用できません: {e}")

    # 会話要約ルート
    try:
        from routes.summary_routes import summary_bp

        app.register_blueprint(summary_bp)
        print("✅ 会話要約ルートを登録しました (/api/summary/*)")
    except ImportError as e:
        print(f"⚠️ 会話要約ルートは利用できません: {e}")

    # 学習分析ルート
    try:
        from routes.analytics_routes import analytics_bp

        app.register_blueprint(analytics_bp)
        print("✅ 学習分析ルートを登録しました (/api/analytics/*)")
    except ImportError as e:
        print(f"⚠️ 学習分析ルートは利用できません: {e}")

    # データエクスポートルート
    try:
        from routes.export_routes import export_bp

        app.register_blueprint(export_bp)
        print("✅ データエクスポートルートを登録しました (/api/export/*)")
    except ImportError as e:
        print(f"⚠️ データエクスポートルートは利用できません: {e}")

    # チュートリアルルート
    try:
        from routes.tutorial_routes import tutorial_bp

        app.register_blueprint(tutorial_bp)
        print("✅ チュートリアルルートを登録しました (/api/tutorial/*)")
    except ImportError as e:
        print(f"⚠️ チュートリアルルートは利用できません: {e}")

    # 3者会話ルート
    try:
        from routes.three_way_routes import three_way_bp

        app.register_blueprint(three_way_bp)
        print("✅ 3者会話ルートを登録しました (/api/three-way/*)")
    except ImportError as e:
        print(f"⚠️ 3者会話ルートは利用できません: {e}")

    # ゲーミフィケーション・ダッシュボード画面
    try:
        from routes.gamification_page_routes import gamification_page_bp

        app.register_blueprint(gamification_page_bp)
        print("✅ ゲーミフィケーション画面を登録しました (/gamification)")
    except ImportError as e:
        print(f"⚠️ ゲーミフィケーション画面は利用できません: {e}")
