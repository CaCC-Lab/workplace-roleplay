"""
モデル関連のルート定義
LLMモデル選択や情報取得のHTTPエンドポイントを管理
"""
from flask import Blueprint, request, jsonify
from typing import Dict, Any

from services.llm_service import LLMService
from services.session_service import SessionService
from errors import ValidationError


# Blueprintの作成
model_bp = Blueprint('model', __name__)


@model_bp.route('/api/models', methods=['GET'])
def get_models():
    """
    利用可能なモデルのリストを取得するエンドポイント
    
    Returns:
        モデル情報を含むJSONレスポンス
    """
    try:
        models = LLMService.get_available_models()
        
        # 現在選択されているモデルを取得
        selected_model = SessionService.get_session_data('selected_model', 'gemini-1.5-flash')
        
        # モデル情報を整形
        model_list = []
        for model_id, info in models.items():
            model_list.append({
                'id': model_id,
                'name': model_id.replace('gemini/', ''),
                'description': info['description'],
                'selected': selected_model == model_id.replace('gemini/', '')
            })
        
        return jsonify({
            'models': model_list,
            'selected': selected_model
        })
        
    except Exception as e:
        print(f"Get models error: {str(e)}")
        return jsonify({
            'models': [],
            'error': 'モデル情報の取得に失敗しました'
        }), 200  # エラーでも200を返して、空のリストを表示


@model_bp.route('/api/select_model', methods=['POST'])
def select_model():
    """
    使用するモデルを選択するエンドポイント
    
    Request JSON:
        - model: 選択するモデル名
        
    Returns:
        成功メッセージを含むJSONレスポンス
    """
    try:
        data = request.json
        model_name = data.get('model')
        
        if not model_name:
            return jsonify({'error': 'モデル名が指定されていません'}), 400
        
        # モデル名の正規化（gemini/プレフィックスを除去）
        if model_name.startswith('gemini/'):
            model_name = model_name.replace('gemini/', '')
        
        # 利用可能なモデルかチェック
        available_models = LLMService.get_available_models()
        full_model_name = f"gemini/{model_name}"
        
        if full_model_name not in available_models:
            return jsonify({
                'error': 'サポートされていないモデルです',
                'available_models': list(available_models.keys())
            }), 400
        
        # セッションに保存
        SessionService.set_session_data('selected_model', model_name)
        
        return jsonify({
            'message': f'モデルを {model_name} に切り替えました',
            'model': model_name
        })
        
    except Exception as e:
        print(f"Select model error: {str(e)}")
        return jsonify({'error': 'モデル選択に失敗しました'}), 500


@model_bp.route('/api/model_info/<model_name>', methods=['GET'])
def get_model_info(model_name: str):
    """
    特定のモデルの詳細情報を取得するエンドポイント
    
    Args:
        model_name: モデル名
        
    Returns:
        モデルの詳細情報を含むJSONレスポンス
    """
    try:
        # モデル名の正規化
        if not model_name.startswith('gemini/'):
            model_name = f"gemini/{model_name}"
        
        available_models = LLMService.get_available_models()
        
        if model_name not in available_models:
            return jsonify({'error': 'モデルが見つかりません'}), 404
        
        model_info = available_models[model_name]
        return jsonify({
            'id': model_name,
            'name': model_name.replace('gemini/', ''),
            'description': model_info['description'],
            'temperature': model_info['temperature'],
            'max_tokens': model_info['max_tokens']
        })
        
    except Exception as e:
        print(f"Get model info error: {str(e)}")
        return jsonify({'error': 'モデル情報の取得に失敗しました'}), 500