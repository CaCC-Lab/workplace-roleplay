"""
LLM (Language Model) 管理サービス
Gemini APIとの統合、モデル初期化、エラーハンドリングを担当
"""
import os
from typing import Optional, Dict, List, Any, Tuple
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

from api_key_manager import (
    get_google_api_key,
    handle_api_error,
    record_api_usage
)
from errors import (
    AuthenticationError,
    ValidationError,
    ExternalAPIError,
    handle_llm_specific_error
)
from config import get_cached_config


class LLMService:
    """LLM管理のためのサービスクラス"""
    
    # 利用可能なGeminiモデル定義
    AVAILABLE_MODELS = {
        "gemini/gemini-1.5-pro": {
            "description": "最新の高性能モデル。長文理解と生成に優れています。",
            "temperature": 0.7,
            "max_tokens": 8192
        },
        "gemini/gemini-1.5-flash": {
            "description": "高速な応答が可能な軽量モデル。日常的な会話に最適です。", 
            "temperature": 0.9,
            "max_tokens": 4096
        }
    }
    
    @staticmethod
    def get_available_models() -> Dict[str, Dict[str, Any]]:
        """
        利用可能なGeminiモデルの情報を返す
        
        Returns:
            モデル情報の辞書
        """
        config = get_cached_config()
        api_key = config.GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            return {}
        
        try:
            # Gemini APIキーの設定
            genai.configure(api_key=api_key)
            
            # 実際に利用可能なモデルを確認
            available_models = {}
            for model_name, model_info in LLMService.AVAILABLE_MODELS.items():
                available_models[model_name] = model_info
            
            return available_models
            
        except Exception as e:
            print(f"Error fetching Gemini models: {e}")
            return {}
    
    @staticmethod
    def create_llm(model_name: str = "gemini-1.5-flash") -> ChatGoogleGenerativeAI:
        """
        Gemini LLMインスタンスを作成
        
        Args:
            model_name: 使用するモデル名
            
        Returns:
            ChatGoogleGenerativeAI インスタンス
            
        Raises:
            AuthenticationError: APIキーが無効な場合
            ValidationError: モデル名が無効な場合
        """
        # APIキーマネージャーから動的にキーを取得
        try:
            GOOGLE_API_KEY = get_google_api_key()
        except Exception as e:
            raise AuthenticationError("Google APIキーの取得に失敗しました")
        
        if not GOOGLE_API_KEY:
            raise AuthenticationError("GOOGLE_API_KEY環境変数が設定されていません")
            
        # APIキーの形式を検証
        if not GOOGLE_API_KEY.startswith("AI"):
            raise AuthenticationError("無効なGoogle APIキー形式です")
        
        # モデル名の検証
        full_model_name = model_name if model_name.startswith("gemini/") else f"gemini/{model_name}"
        if full_model_name not in LLMService.AVAILABLE_MODELS:
            raise ValidationError(
                f"サポートされていないモデル: {model_name}",
                field="model_name",
                details={"available_models": list(LLMService.AVAILABLE_MODELS.keys())}
            )
        
        model_config = LLMService.AVAILABLE_MODELS[full_model_name]
        
        # モデル名を簡潔な形式に変換（"gemini/"プレフィックスを除去）
        simple_model_name = full_model_name.replace("gemini/", "")
        
        # ChatGoogleGenerativeAIインスタンスを作成
        try:
            llm = ChatGoogleGenerativeAI(
                model=simple_model_name,
                google_api_key=GOOGLE_API_KEY,
                temperature=model_config["temperature"],
                max_output_tokens=model_config["max_tokens"],
                convert_system_message_to_human=True,
                streaming=True
            )
            
            # 使用記録
            record_api_usage(GOOGLE_API_KEY)
            
            return llm
            
        except Exception as e:
            # APIキーエラーとして記録
            handle_api_error(GOOGLE_API_KEY, e)
            
            # 特定のエラータイプに変換
            raise handle_llm_specific_error(e, "Gemini")
    
    @staticmethod
    def initialize_llm(model_name: str) -> ChatGoogleGenerativeAI:
        """
        指定されたモデル名でLLMを初期化（互換性のためのエイリアス）
        
        Args:
            model_name: 使用するモデル名
            
        Returns:
            初期化されたLLMインスタンス
        """
        return LLMService.create_llm(model_name)
    
    @staticmethod
    def extract_content(resp: Any) -> str:
        """
        LLMレスポンスから内容を抽出
        
        Args:
            resp: LLMのレスポンス
            
        Returns:
            抽出されたテキスト内容
        """
        if hasattr(resp, 'content'):
            return resp.content
        elif hasattr(resp, 'text'):
            return resp.text
        elif isinstance(resp, str):
            return resp
        elif isinstance(resp, dict) and 'content' in resp:
            return resp['content']
        elif isinstance(resp, dict) and 'text' in resp:
            return resp['text']
        else:
            return str(resp)
    
    @staticmethod
    def create_chat_prompt(system_prompt: str, include_history: bool = True) -> ChatPromptTemplate:
        """
        チャット用のプロンプトテンプレートを作成
        
        Args:
            system_prompt: システムプロンプト
            include_history: 履歴を含めるかどうか
            
        Returns:
            ChatPromptTemplate インスタンス
        """
        if include_history:
            return ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}")
            ])
        else:
            return ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}")
            ])
    
    @staticmethod
    def add_messages_from_history(messages: List[BaseMessage], history: List[Dict[str, str]], 
                                max_entries: int = 5) -> None:
        """
        会話履歴からメッセージを追加
        
        Args:
            messages: メッセージリスト
            history: 会話履歴
            max_entries: 追加する最大エントリ数
        """
        recent_history = history[-max_entries:] if len(history) > max_entries else history
        
        for entry in recent_history:
            if 'user' in entry:
                messages.append(HumanMessage(content=entry['user']))
            if 'assistant' in entry:
                messages.append(AIMessage(content=entry['assistant']))
    
    @staticmethod
    def try_multiple_models_for_prompt(prompt: str) -> Tuple[str, str, Optional[str]]:
        """
        複数のモデルでプロンプトを試行
        
        Args:
            prompt: 実行するプロンプト
            
        Returns:
            (コンテンツ, 使用したモデル名, エラーメッセージ)のタプル
        """
        models_to_try = ["gemini-1.5-flash", "gemini-1.5-pro"]
        last_error = None
        
        for model_name in models_to_try:
            try:
                llm = LLMService.create_llm(model_name)
                result = llm.invoke(prompt)
                content = LLMService.extract_content(result)
                return content, model_name, None
            except Exception as e:
                last_error = str(e)
                print(f"Model {model_name} failed: {last_error}")
                continue
        
        # すべてのモデルで失敗した場合
        error_msg = f"すべてのモデルで生成に失敗しました。最後のエラー: {last_error}"
        return "", "", error_msg