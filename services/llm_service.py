"""
LLM（Language Model）関連のサービス
"""
import os
import hashlib
from typing import Optional, Dict, List, Any, Union
from datetime import datetime
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, BaseMessage
from pydantic import SecretStr

from errors import ExternalAPIError

# ConfigurationErrorを定義
class ConfigurationError(Exception):
    """設定エラー"""
    pass


class LLMService:
    """LLM関連の操作を管理するサービスクラス"""
    
    def __init__(self):
        self.api_key = os.environ.get('GOOGLE_API_KEY')
        if not self.api_key:
            raise ConfigurationError("GOOGLE_API_KEY環境変数が設定されていません")
        
        # Gemini APIの設定
        genai.configure(api_key=self.api_key)
        
        # 利用可能なモデルのキャッシュ
        self._available_models_cache = None
        self._cache_timestamp = None
        self._cache_duration = 300  # 5分間キャッシュ
        
        # レスポンスキャッシュ
        self._response_cache = {}
        self._cache_max_size = 100  # 最大100件のレスポンスをキャッシュ
    
    def get_available_gemini_models(self) -> List[Dict[str, Any]]:
        """利用可能なGeminiモデルのリストを取得"""
        now = datetime.now()
        
        # キャッシュが有効な場合はそれを返す
        if (self._available_models_cache and 
            self._cache_timestamp and 
            (now - self._cache_timestamp).seconds < self._cache_duration):
            return self._available_models_cache
        
        try:
            models = []
            supported_models = {
                "gemini-1.5-flash": {
                    "display_name": "Gemini 1.5 Flash",
                    "description": "高速で効率的なモデル",
                    "context_window": 1048576,
                    "capabilities": ["text", "vision", "function_calling"]
                },
                "gemini-1.5-pro": {
                    "display_name": "Gemini 1.5 Pro",
                    "description": "高性能で精度の高いモデル",
                    "context_window": 2097152,
                    "capabilities": ["text", "vision", "function_calling"]
                },
                "gemini-2.0-flash-exp": {
                    "display_name": "Gemini 2.0 Flash (実験版)",
                    "description": "次世代の高速モデル（実験版）",
                    "context_window": 1048576,
                    "capabilities": ["text", "vision", "function_calling", "multimodal"]
                }
            }
            
            # APIから利用可能なモデルを取得
            for model in genai.list_models():
                model_name = model.name.replace("models/", "")
                
                if model_name in supported_models:
                    model_info = {
                        "name": model_name,
                        "display_name": supported_models[model_name]["display_name"],
                        "description": supported_models[model_name]["description"],
                        "context_window": supported_models[model_name]["context_window"],
                        "capabilities": supported_models[model_name]["capabilities"],
                        "supported_generation_methods": model.supported_generation_methods
                    }
                    models.append(model_info)
            
            # キャッシュを更新
            self._available_models_cache = models
            self._cache_timestamp = now
            
            return models
            
        except Exception as e:
            print(f"Geminiモデルリストの取得エラー: {e}")
            # エラー時はデフォルトのモデルリストを返す
            return self._get_default_models()
    
    def _get_default_models(self) -> List[Dict[str, Any]]:
        """デフォルトのモデルリストを返す"""
        return [
            {
                "name": "gemini-1.5-flash",
                "display_name": "Gemini 1.5 Flash",
                "description": "高速で効率的なモデル",
                "context_window": 1048576,
                "capabilities": ["text"],
                "supported_generation_methods": ["generateContent", "streamGenerateContent"]
            },
            {
                "name": "gemini-1.5-pro",
                "display_name": "Gemini 1.5 Pro",
                "description": "高性能で精度の高いモデル",
                "context_window": 2097152,
                "capabilities": ["text"],
                "supported_generation_methods": ["generateContent", "streamGenerateContent"]
            }
        ]
    
    def create_gemini_llm(self, model_name: str = "gemini-1.5-flash") -> ChatGoogleGenerativeAI:
        """Gemini LLMインスタンスを作成"""
        try:
            # モデル設定
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
            
            # 安全性設定
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
            
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=SecretStr(self.api_key),
                temperature=generation_config["temperature"],
                top_p=generation_config["top_p"],
                top_k=generation_config["top_k"],
                max_output_tokens=generation_config["max_output_tokens"],
                safety_settings=safety_settings,
                convert_system_message_to_human=True
            )
            
        except Exception as e:
            raise ExternalAPIError(f"Gemini LLMの作成に失敗しました: {str(e)}")
    
    def initialize_llm(self, model_name: str) -> ChatGoogleGenerativeAI:
        """指定されたモデル名でLLMを初期化"""
        # Geminiモデルの場合
        if "gemini" in model_name.lower():
            return self.create_gemini_llm(model_name)
        else:
            # デフォルトでGeminiを使用
            return self.create_gemini_llm("gemini-1.5-flash")
    
    def create_and_get_response(
        self, 
        llm: Any, 
        messages_or_prompt: Union[List[BaseMessage], str], 
        extract: bool = True,
        use_cache: bool = True
    ) -> str:
        """LLMから応答を取得（キャッシュ機能付き）"""
        try:
            if isinstance(messages_or_prompt, str):
                # 文字列の場合はHumanMessageに変換
                messages = [HumanMessage(content=messages_or_prompt)]
            else:
                messages = messages_or_prompt
            
            # キャッシュ機能を使用する場合
            if use_cache:
                cache_key = self._generate_cache_key(messages, llm.model_name if hasattr(llm, 'model_name') else 'default')
                cached_response = self._get_cached_response(cache_key)
                if cached_response:
                    import logging
                    logging.info(f"Using cached response for key: {cache_key[:16]}...")
                    return cached_response
            
            response = llm.invoke(messages)
            
            if extract:
                content = self.extract_content(response)
                # キャッシュに保存
                if use_cache:
                    self._cache_response(cache_key, content)
                return content
            return response
            
        except Exception as e:
            raise ExternalAPIError(f"LLM応答の取得に失敗しました: {str(e)}")
    
    def extract_content(self, resp: Any) -> str:
        """レスポンスからコンテンツを抽出"""
        if resp is None:
            return ""
        
        if isinstance(resp, str):
            return resp
        
        if hasattr(resp, 'content'):
            return str(resp.content)
        
        if hasattr(resp, 'text'):
            return str(resp.text)
        
        if isinstance(resp, dict):
            if 'content' in resp:
                return str(resp['content'])
            if 'text' in resp:
                return str(resp['text'])
            if 'message' in resp:
                if isinstance(resp['message'], dict) and 'content' in resp['message']:
                    return str(resp['message']['content'])
                return str(resp['message'])
        
        return str(resp)
    
    def get_all_available_models(self) -> List[Dict[str, Any]]:
        """すべての利用可能なモデルを取得"""
        all_models = []
        
        # Geminiモデルを追加
        gemini_models = self.get_available_gemini_models()
        for model in gemini_models:
            model["provider"] = "Google"
            all_models.append(model)
        
        # 将来的に他のプロバイダーのモデルも追加可能
        
        return all_models
    
    def handle_llm_error(
        self, 
        error: Exception, 
        fallback_model: str = "gemini-1.5-flash"
    ) -> Optional[ChatGoogleGenerativeAI]:
        """LLMエラーをハンドリングし、フォールバックモデルを返す"""
        error_message = str(error).lower()
        
        # レート制限エラーの場合
        if "rate limit" in error_message or "429" in error_message:
            print(f"レート制限エラー: {error}")
            # より低速なモデルにフォールバック
            if fallback_model != "gemini-1.5-flash":
                return self.create_gemini_llm("gemini-1.5-flash")
        
        # APIキーエラーの場合
        elif "api key" in error_message or "401" in error_message:
            print(f"APIキー認証エラー: {error}")
            raise ConfigurationError("APIキーが無効です")
        
        # モデルが利用できない場合
        elif "model not found" in error_message or "404" in error_message:
            print(f"モデルが見つかりません: {error}")
            return self.create_gemini_llm(fallback_model)
        
        # その他のエラー
        else:
            print(f"予期しないLLMエラー: {error}")
            return None
    
    def _generate_cache_key(self, messages: List[BaseMessage], model_name: str) -> str:
        """メッセージとモデル名からキャッシュキーを生成"""
        # メッセージを文字列に変換
        messages_str = ""
        for msg in messages:
            if hasattr(msg, 'content'):
                messages_str += f"{msg.__class__.__name__}:{msg.content}|"
        
        # モデル名を追加
        cache_string = f"{model_name}:{messages_str}"
        
        # ハッシュ化
        return hashlib.sha256(cache_string.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """キャッシュから応答を取得"""
        return self._response_cache.get(cache_key)
    
    def _cache_response(self, cache_key: str, content: str) -> None:
        """応答をキャッシュに保存"""
        # キャッシュサイズ制限チェック
        if len(self._response_cache) >= self._cache_max_size:
            # 最も古いエントリを削除（簡易的なLRU）
            oldest_key = next(iter(self._response_cache))
            del self._response_cache[oldest_key]
        
        self._response_cache[cache_key] = content
    
    def clear_response_cache(self) -> None:
        """レスポンスキャッシュをクリア"""
        self._response_cache.clear()