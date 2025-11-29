"""
Model routes for the workplace-roleplay application.
Handles model listing and feature flags API endpoints.
"""

import secrets

from config.feature_flags import (
    FeatureFlags,
    get_feature_flags,
    is_model_selection_enabled,
)
from flask import Blueprint, jsonify, request, session

from config import get_cached_config
from errors import with_error_handling

# Blueprint作成
model_bp = Blueprint("model", __name__)

# 設定の取得
config = get_cached_config()


def get_all_available_models():
    """
    すべての利用可能なモデルを取得し、カテゴリ別に整理する
    """
    try:
        import google.generativeai as genai

        api_key = config.GOOGLE_API_KEY
        if not api_key:
            return _get_fallback_models()

        genai.configure(api_key=api_key)
        models = genai.list_models()

        gemini_models = []
        for model in models:
            if "gemini" in model.name.lower():
                model_short_name = model.name.split("/")[-1]
                model_name = f"gemini/{model_short_name}"
                gemini_models.append(model_name)

        model_dicts = []
        for model_id in gemini_models:
            model_dicts.append(
                {"id": model_id, "name": model_id.split("/")[-1], "provider": "gemini"}
            )

        return {"models": model_dicts, "categories": {"gemini": model_dicts}}
    except Exception as e:
        print(f"Error fetching models: {str(e)}")
        return _get_fallback_models()


def _get_fallback_models():
    """フォールバック用のモデルリストを返す"""
    basic_models = [
        {"id": "gemini/gemini-1.5-pro", "name": "gemini-1.5-pro", "provider": "gemini"},
        {
            "id": "gemini/gemini-1.5-flash",
            "name": "gemini-1.5-flash",
            "provider": "gemini",
        },
    ]
    return {"models": basic_models, "categories": {"gemini": basic_models}}


@model_bp.route("/api/models", methods=["GET"])
@with_error_handling
def api_models():
    """利用可能なGeminiモデル一覧を返す"""
    if not is_model_selection_enabled():
        return jsonify(
            {
                "models": [
                    {"name": config.DEFAULT_MODEL, "display_name": "Default Model"}
                ],
                "feature_disabled": True,
                "message": "モデル選択機能は現在無効化されています。",
            }
        )

    model_info = get_all_available_models()
    return jsonify(model_info)


@model_bp.route("/api/feature_flags", methods=["GET"])
@with_error_handling
def api_feature_flags():
    """機能フラグの状態を返すAPI"""
    try:
        flags = get_feature_flags()
        return jsonify(flags.to_dict())
    except Exception as e:
        print(f"Error getting feature flags: {str(e)}")
        return jsonify({"error": "Failed to get feature flags"}), 500


@model_bp.route("/api/csrf-token", methods=["GET"])
def get_csrf_token():
    """CSRFトークンを取得するエンドポイント"""
    try:
        from utils.security import CSRFToken

        csrf_token = CSRFToken.get_or_create(session)

        return jsonify({"csrf_token": csrf_token, "expires_in": 3600})
    except Exception:
        csrf_token = session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_hex(16)
            session["csrf_token"] = csrf_token
            session.modified = True

        return jsonify({"csrf_token": csrf_token, "expires_in": 3600})


@model_bp.route("/api/key_status", methods=["GET"])
def get_api_key_status():
    """APIキーの使用状況を取得"""
    try:
        from compliant_api_manager import get_compliant_api_manager

        manager = get_compliant_api_manager()
        status = manager.get_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
