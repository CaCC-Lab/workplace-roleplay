"""
観戦モードサービス
AI同士の会話観戦機能を担当
"""
from typing import Dict, Any, List, Optional, Tuple
import json
from datetime import datetime
import random
import logging

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate

from services.llm_service import LLMService
from services.session_service import SessionService
from errors import ValidationError, ExternalAPIError
from utils.security import SecurityUtils


class WatchService:
    """観戦モード機能のためのサービスクラス"""
    
    # AI1のシステムプロンプト
    AI1_SYSTEM_PROMPT = """あなたは「{partner_type}」として会話に参加しています。
{partner_description}

今回の話題: {topic}
{topic_description}

会話の指針:
1. 自然で親しみやすい口調で話してください
2. 相手の発言をよく聞き、適切に反応してください
3. 話題を深めたり、新しい視点を提供してください
4. 日本語で、実際の会話のように自然に話してください
5. 1回の発言は2-3文程度にまとめてください"""
    
    # AI2のシステムプロンプト
    AI2_SYSTEM_PROMPT = """あなたは「{partner_type}」として会話に参加しています。
{partner_description}

今回の話題: {topic}
{topic_description}

会話の指針:
1. 自然で親しみやすい口調で話してください
2. 相手の発言に共感したり、質問したりしてください
3. 自分の経験や意見も交えながら会話を楽しんでください
4. 日本語で、実際の会話のように自然に話してください
5. 1回の発言は2-3文程度にまとめてください"""
    
    # パートナータイプの定義
    PARTNER_TYPES = {
        "同僚": "職場の同僚。仕事の話から日常の話題まで幅広く話せる関係。",
        "友人": "気の置けない友人。趣味や日常生活について楽しく話せる。",
        "先輩": "職場や学校の先輩。アドバイスをくれたり、経験を共有してくれる。",
        "カウンセラー": "優しく話を聞いてくれる相談相手。共感的で支援的。"
    }
    
    # 話題の定義
    TOPICS = {
        "仕事": "仕事の進め方、職場の人間関係、キャリアについてなど。",
        "趣味": "休日の過ごし方、好きなこと、新しく始めたいことなど。",
        "日常": "最近の出来事、天気、食事、健康についてなど。",
        "悩み": "困っていること、相談したいこと、アドバイスが欲しいことなど。"
    }
    
    @staticmethod
    def start_watch_mode(partner1_type: str = None, partner2_type: str = None, 
                        topic: str = None, model_name: str = None) -> Dict[str, Any]:
        """
        観戦モードを開始
        
        Args:
            partner1_type: AI1のタイプ
            partner2_type: AI2のタイプ
            topic: 会話の話題
            model_name: 使用するモデル名
            
        Returns:
            初期設定と最初のメッセージ
        """
        # デフォルト値の設定
        if not partner1_type:
            partner1_type = random.choice(list(WatchService.PARTNER_TYPES.keys()))
        if not partner2_type:
            partner2_type = random.choice(list(WatchService.PARTNER_TYPES.keys()))
        if not topic:
            topic = random.choice(list(WatchService.TOPICS.keys()))
        if not model_name:
            model_name = SessionService.get_session_data('selected_model', 'gemini-1.5-flash')
        
        # セッションの初期化
        SessionService.initialize_session_history('watch_history')
        SessionService.set_session_start_time('watch')
        
        # 設定の保存
        watch_config = {
            'partner1_type': partner1_type,
            'partner2_type': partner2_type,
            'topic': topic,
            'model': model_name,
            'turn': 0
        }
        SessionService.set_session_data('watch_config', watch_config)
        
        # 最初のメッセージを生成
        initial_message = WatchService._generate_initial_message(
            partner1_type, partner2_type, topic, model_name
        )
        
        # 履歴に追加
        SessionService.add_to_session_history('watch_history', {
            'speaker': 'AI1',
            'partner_type': partner1_type,
            'message': initial_message,
            'timestamp': datetime.now().isoformat()
        })
        
        return {
            'config': watch_config,
            'initial_message': initial_message,
            'speaker': 'AI1',
            'partner1_description': WatchService.PARTNER_TYPES.get(partner1_type, ''),
            'partner2_description': WatchService.PARTNER_TYPES.get(partner2_type, ''),
            'topic_description': WatchService.TOPICS.get(topic, '')
        }
    
    @staticmethod
    def generate_next_message() -> Dict[str, Any]:
        """
        次のメッセージを生成
        
        Returns:
            次のメッセージと話者情報
        """
        # 設定の取得
        config = SessionService.get_session_data('watch_config')
        if not config:
            raise ValidationError("観戦モードが開始されていません")
        
        # 履歴の取得
        history = SessionService.get_session_history('watch_history')
        if not history:
            raise ValidationError("会話履歴が見つかりません")
        
        # 次の話者を決定
        last_speaker = history[-1].get('speaker', 'AI1')
        next_speaker = 'AI2' if last_speaker == 'AI1' else 'AI1'
        
        # 対応するパートナータイプ
        if next_speaker == 'AI1':
            partner_type = config['partner1_type']
            system_prompt_template = WatchService.AI1_SYSTEM_PROMPT
        else:
            partner_type = config['partner2_type']
            system_prompt_template = WatchService.AI2_SYSTEM_PROMPT
        
        # LLMの初期化
        llm = LLMService.create_llm(config['model'])
        
        # システムプロンプトの作成
        system_prompt = system_prompt_template.format(
            partner_type=partner_type,
            partner_description=WatchService.PARTNER_TYPES[partner_type],
            topic=config['topic'],
            topic_description=WatchService.TOPICS[config['topic']]
        )
        
        # 会話履歴からメッセージを構築
        messages = [SystemMessage(content=system_prompt)]
        
        # 最近の会話を含める（最大10ターン）
        recent_history = history[-10:] if len(history) > 10 else history
        for entry in recent_history:
            speaker = entry.get('speaker', 'AI1')
            content = entry.get('message', '')
            
            if speaker == next_speaker:
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))
        
        try:
            # 次のメッセージを生成
            response = llm.invoke(messages)
            next_message = LLMService.extract_content(response)
            
            # 履歴に追加
            SessionService.add_to_session_history('watch_history', {
                'speaker': next_speaker,
                'partner_type': partner_type,
                'message': next_message,
                'timestamp': datetime.now().isoformat()
            })
            
            # ターン数を更新
            config['turn'] += 1
            SessionService.set_session_data('watch_config', config)
            
            return {
                'speaker': next_speaker,
                'partner_type': partner_type,
                'message': next_message,
                'turn': config['turn']
            }
            
        except Exception as e:
            print(f"Watch mode message generation error: {str(e)}")
            raise ExternalAPIError("Gemini", "メッセージ生成に失敗しました", str(e))
    
    @staticmethod
    def _generate_initial_message(partner1_type: str, partner2_type: str, 
                                 topic: str, model_name: str) -> str:
        """
        最初のメッセージを生成
        
        Args:
            partner1_type: AI1のタイプ
            partner2_type: AI2のタイプ
            topic: 話題
            model_name: モデル名
            
        Returns:
            生成されたメッセージ
        """
        # プロンプトの作成
        prompt = f"""あなたは「{partner1_type}」として、「{partner2_type}」との会話を始めようとしています。
話題は「{topic}」です。

自然な挨拶から始めて、この話題について話を始めてください。
1-2文程度の短い発言にしてください。

例:
- 「お疲れ様！最近{topic}のことで気になることがあってさ...」
- 「ねえ、{topic}について聞いてもいい？」
"""
        
        try:
            llm = LLMService.create_llm(model_name)
            response = llm.invoke(prompt)
            return LLMService.extract_content(response)
        except Exception as e:
            # フォールバックメッセージ
            return f"あ、ちょうどよかった！{topic}について話したいことがあったんだ。"
    
    @staticmethod
    def get_watch_summary() -> Dict[str, Any]:
        """
        観戦モードの要約を取得
        
        Returns:
            会話の要約情報
        """
        config = SessionService.get_session_data('watch_config', {})
        history = SessionService.get_session_history('watch_history')
        
        if not history:
            return {
                'summary': '会話履歴がありません',
                'turn_count': 0
            }
        
        # 基本情報
        if config is None:
            config = {}
        
        summary_info = {
            'turn_count': len(history),
            'partner1_type': config.get('partner1_type', '不明') if isinstance(config, dict) else '不明',
            'partner2_type': config.get('partner2_type', '不明') if isinstance(config, dict) else '不明',
            'topic': config.get('topic', '不明') if isinstance(config, dict) else '不明',
            'start_time': SessionService.get_session_start_time('watch')
        }
        
        # 会話の要約を生成（オプション）
        if len(history) >= 3:
            try:
                summary_prompt = "以下の会話を50文字程度で要約してください:\n\n"
                for entry in history[-5:]:  # 最後の5つのメッセージ
                    summary_prompt += f"{entry['partner_type']}: {entry['message']}\n"
                
                summary_text, _, _ = LLMService.try_multiple_models_for_prompt(summary_prompt)
                summary_info['summary'] = summary_text
            except:
                summary_info['summary'] = '会話の要約生成に失敗しました'
        
        return summary_info
    
    @staticmethod
    def _extract_message_content(resp: Any) -> str:
        """
        レスポンスからメッセージ内容を抽出（プライベートメソッド）
        
        Args:
            resp: LLMのレスポンス
            
        Returns:
            抽出されたメッセージ内容
        """
        return LLMService.extract_content(resp)