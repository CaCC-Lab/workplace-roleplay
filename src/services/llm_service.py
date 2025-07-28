"""LLMサービス"""
import time
from typing import Dict, List, Optional, Any
from threading import Lock

from flask import current_app


class LLMService:
    """Language Model管理サービス"""
    
    def __init__(self):
        self._model_cache: Dict[str, Any] = {}
        self._cache_lock = Lock()
        self._cache_ttl = 3600  # 1時間
        self._llm_instances: Dict[str, Any] = {}
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """利用可能なモデルのリストを返す
        
        Returns:
            モデル情報のリスト
        """
        # 設定から固定リストを取得（API呼び出しを避ける）
        models = current_app.config.get("AVAILABLE_MODELS", [])
        
        result = []
        for model_id in models:
            model_name = model_id.split("/")[-1]
            result.append({
                "id": model_id,
                "name": model_name,
                "provider": "gemini"
            })
        
        return result
    
    def get_llm(self, model_name: str) -> Optional[Any]:
        """LLMインスタンスを取得（遅延初期化）
        
        Args:
            model_name: モデル名
            
        Returns:
            LLMインスタンス
        """
        # キャッシュから取得
        if model_name in self._llm_instances:
            return self._llm_instances[model_name]
        
        # API Keyの確認
        api_key = current_app.config.get("GOOGLE_API_KEY")
        if not api_key:
            current_app.logger.warning("GOOGLE_API_KEY is not set")
            return None
        
        try:
            # 遅延インポート
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            # モデル名の正規化
            if model_name.startswith("gemini/"):
                model_name = model_name.replace("gemini/", "")
            
            # LLMインスタンスの作成
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0.7,
                max_output_tokens=2048,
                timeout=30,
                max_retries=2
            )
            
            # キャッシュに保存
            self._llm_instances[model_name] = llm
            
            return llm
            
        except Exception as e:
            current_app.logger.error(f"Failed to create LLM instance: {e}")
            return None
    
    def generate_response(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        **kwargs
    ) -> str:
        """プロンプトに対する応答を生成
        
        Args:
            prompt: プロンプト
            model_name: モデル名（省略時はデフォルトモデル）
            **kwargs: その他のパラメータ
            
        Returns:
            生成された応答
        """
        if model_name is None:
            model_name = current_app.config["DEFAULT_MODEL"]
        
        llm = self.get_llm(model_name)
        if llm is None:
            return "申し訳ありません。現在AIサービスが利用できません。"
        
        try:
            response = llm.invoke(prompt, **kwargs)
            return response.content
        except Exception as e:
            current_app.logger.error(f"LLM generation error: {e}")
            return "申し訳ありません。応答の生成中にエラーが発生しました。"