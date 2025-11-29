"""
LLM（Large Language Model）関連のサービス
Gemini APIとの連携を管理
"""
import asyncio
import os

# プロジェクトルートからインポート
import sys
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import google.generativeai as genai
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from compliant_api_manager import CompliantAPIManager
from config import Config


class LLMService:
    """LLM連携を管理するサービス"""

    # 廃止されたモデルと代替モデルのマッピング
    DEPRECATED_MODELS = {
        "gemini-pro-vision": "gemini-1.5-flash",
        "gemini-1.0-pro-vision": "gemini-1.5-flash",
        "gemini-1.0-pro-vision-latest": "gemini-1.5-flash-latest",
        "gemini-pro": "gemini-1.5-flash",  # gemini-proも新しいモデルに置き換え
        "gemini-1.0-pro": "gemini-1.5-flash",
    }

    # 利用可能なGeminiモデル（実際のAPI応答に基づく）
    AVAILABLE_MODELS = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-8b",
        "gemini-1.5-flash-8b-latest",
        "gemini-1.5-pro",
        "gemini-1.5-pro-latest",
        "gemini-1.0-pro",
        "gemini-1.0-pro-latest",
    ]

    def __init__(self, config: Optional[Config] = None):
        """
        LLMServiceの初期化

        Args:
            config: 設定オブジェクト（オプション）
        """
        self.config = config or Config()
        self.api_key_manager = CompliantAPIManager()
        self.models = {}
        self.default_temperature = self.config.DEFAULT_TEMPERATURE

        # Gemini APIの初期化
        self._initialize_genai()

    def _initialize_genai(self):
        """Gemini APIの初期化"""
        try:
            # APIキーマネージャーからキーを取得
            api_key = self.api_key_manager.get_api_key()
            genai.configure(api_key=api_key)
        except Exception as e:
            print(f"Warning: Failed to initialize Gemini API: {e}")

    def create_gemini_llm(
        self, model_name: str = "gemini-1.5-flash"
    ) -> ChatGoogleGenerativeAI:
        """
        LangChainのGemini Chat modelインスタンス生成
        廃止されたモデルを自動的に代替モデルに置き換える

        Args:
            model_name: 使用するモデル名

        Returns:
            ChatGoogleGenerativeAI: LangChainのGeminiモデルインスタンス
        """
        try:
            # 廃止されたモデルの場合は代替モデルに置き換え
            if model_name in self.DEPRECATED_MODELS:
                original_model = model_name
                model_name = self.DEPRECATED_MODELS[model_name]
                print(
                    f"Model '{original_model}' is deprecated. Using '{model_name}' instead."
                )

            # APIキーマネージャーからキーを取得
            current_api_key = self.api_key_manager.get_api_key()

            # モデルインスタンスを作成
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=current_api_key,
                temperature=self.default_temperature,
                convert_system_message_to_human=True,
                streaming=True,
            )

            # 使用回数を記録
            self.api_key_manager.record_successful_request(current_api_key)

            return llm

        except Exception as e:
            # エラーを記録
            self.api_key_manager.record_failed_request(current_api_key, e)
            print(f"Error creating Gemini LLM: {str(e)}")
            raise

    def initialize_llm(self, model_name: str) -> ChatGoogleGenerativeAI:
        """
        モデル名に基づいて適切なLLMを初期化

        Args:
            model_name: 使用するモデル名

        Returns:
            ChatGoogleGenerativeAI: 初期化されたLLMインスタンス
        """
        try:
            # gemini/プレフィックスを削除
            if model_name.startswith("gemini/"):
                model_name = model_name.replace("gemini/", "")

            return self.create_gemini_llm(model_name)
        except Exception as e:
            print(f"Error in initialize_llm: {str(e)}")
            raise

    def get_or_create_model(self, model_name: str) -> ChatGoogleGenerativeAI:
        """
        モデルを取得または作成（キャッシュ機能付き）

        Args:
            model_name: 使用するモデル名

        Returns:
            ChatGoogleGenerativeAI: LLMインスタンス
        """
        if model_name not in self.models:
            self.models[model_name] = self.initialize_llm(model_name)
        return self.models[model_name]

    async def stream_chat_response(
        self,
        message: str,
        history: List[Dict[str, str]],
        model_name: str = "gemini-1.5-flash",
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        チャットレスポンスをストリーミングで生成

        Args:
            message: ユーザーからのメッセージ
            history: 会話履歴
            model_name: 使用するモデル名
            system_prompt: システムプロンプト（オプション）

        Yields:
            str: レスポンスのチャンク
        """
        try:
            # モデルを取得
            llm = self.get_or_create_model(model_name)

            # メッセージ履歴を構築
            messages = self._build_messages(history, message, system_prompt)

            # ストリーミングレスポンスを生成
            accumulated_response = ""
            async for chunk in llm.astream(messages):
                if chunk.content:
                    accumulated_response += chunk.content
                    yield chunk.content

            # レスポンスが空の場合はエラー
            if not accumulated_response:
                yield "申し訳ございません。応答の生成に失敗しました。"

        except Exception as e:
            print(f"Error in stream_chat_response: {str(e)}")
            yield f"エラーが発生しました: {str(e)}"

    def _build_messages(
        self,
        history: List[Dict[str, str]],
        current_message: str,
        system_prompt: Optional[str] = None,
    ) -> List[Union[SystemMessage, HumanMessage, AIMessage]]:
        """
        LangChain用のメッセージリストを構築

        Args:
            history: 会話履歴
            current_message: 現在のメッセージ
            system_prompt: システムプロンプト

        Returns:
            List: LangChainメッセージのリスト
        """
        messages = []

        # システムプロンプトがある場合は追加
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        # 履歴からメッセージを構築
        for entry in history:
            if isinstance(entry, dict):
                if "human" in entry:
                    messages.append(HumanMessage(content=entry["human"]))
                if "ai" in entry:
                    messages.append(AIMessage(content=entry["ai"]))

        # 現在のメッセージを追加
        messages.append(HumanMessage(content=current_message))

        return messages

    def invoke_sync(
        self,
        messages_or_prompt: Union[str, List],
        model_name: str = "gemini-1.5-flash",
        extract_content: bool = True,
    ) -> Union[str, Any]:
        """
        同期的にLLMを呼び出す（後方互換性のため）

        Args:
            messages_or_prompt: プロンプトまたはメッセージリスト
            model_name: 使用するモデル名
            extract_content: レスポンスからコンテンツを抽出するか

        Returns:
            Union[str, Any]: レスポンス
        """
        try:
            llm = self.get_or_create_model(model_name)
            response = llm.invoke(messages_or_prompt)

            if extract_content and hasattr(response, "content"):
                return response.content
            return response
        except Exception as e:
            print(f"Error in invoke_sync: {str(e)}")
            raise

    def get_available_models(self) -> List[str]:
        """
        利用可能なモデルのリストを返す

        Returns:
            List[str]: 利用可能なモデル名のリスト
        """
        return self.AVAILABLE_MODELS.copy()

    def cleanup(self):
        """
        リソースのクリーンアップ
        """
        self.models.clear()
