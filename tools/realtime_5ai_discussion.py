#!/usr/bin/env python3
"""
リアルタイム5AI議論システム
複数のAIが同時並行で議論し、効率的に合意形成を行うシステム

特徴:
- 並列処理による高速議論
- WebSocketによるリアルタイム通信
- 議論の可視化とログ記録
- 自動合意形成メカニズム
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
from concurrent.futures import ThreadPoolExecutor
import subprocess
import os


# AIモデルの定義
class AIModel(Enum):
    CLAUDE_4 = "claude-opus-4-1"
    GEMINI_25 = "gemini-2.5-flash"
    QWEN3_CODER = "qwen3-coder"
    GPT_5 = "gpt-5"
    CURSOR = "cursor-agent"


@dataclass
class AIParticipant:
    """AI参加者の定義"""

    model: AIModel
    role: str
    expertise: List[str]
    command: str  # 実行コマンド（gemini, qwen, codex等）
    active: bool = True
    response_time: float = 0.0


@dataclass
class Message:
    """議論メッセージ"""

    id: str
    sender: AIModel
    content: str
    timestamp: datetime
    in_reply_to: Optional[str] = None
    message_type: str = "statement"  # statement, question, answer, agreement, objection
    confidence: float = 1.0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "sender": self.sender.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "in_reply_to": self.in_reply_to,
            "type": self.message_type,
            "confidence": self.confidence,
        }


@dataclass
class DiscussionTopic:
    """議論トピック"""

    title: str
    description: str
    context: str
    objectives: List[str]
    constraints: List[str]
    deadline_seconds: int = 1800  # 30分デフォルト


class RealtimeDiscussionOrchestrator:
    """リアルタイム5AI議論オーケストレーター"""

    def __init__(self):
        self.participants = self._initialize_participants()
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.message_history: List[Message] = []
        self.consensus_tracker: Dict[str, List[AIModel]] = {}
        self.start_time: Optional[datetime] = None
        self.executor = ThreadPoolExecutor(max_workers=5)

    def _initialize_participants(self) -> Dict[AIModel, AIParticipant]:
        """AI参加者の初期化"""
        return {
            AIModel.CLAUDE_4: AIParticipant(
                model=AIModel.CLAUDE_4,
                role="システムアーキテクト",
                expertise=["architecture", "quality", "design_patterns"],
                command="claude",  # Claude APIを呼び出す仮想コマンド
            ),
            AIModel.GEMINI_25: AIParticipant(
                model=AIModel.GEMINI_25,
                role="セキュリティ＆最新技術スペシャリスト",
                expertise=["security", "latest_tech", "web_search"],
                command="gemini",
            ),
            AIModel.QWEN3_CODER: AIParticipant(
                model=AIModel.QWEN3_CODER,
                role="実装リード",
                expertise=["coding", "performance", "optimization"],
                command="qwen",
            ),
            AIModel.GPT_5: AIParticipant(
                model=AIModel.GPT_5,
                role="ソリューションアーキテクト",
                expertise=["problem_solving", "edge_cases", "business"],
                command="codex",
            ),
            AIModel.CURSOR: AIParticipant(
                model=AIModel.CURSOR,
                role="DevOps＆開発者体験",
                expertise=["devops", "ci_cd", "developer_experience"],
                command="cursor-agent",
            ),
        }

    async def call_ai_parallel(self, ai_model: AIModel, prompt: str) -> str:
        """AIを並列で呼び出し"""
        participant = self.participants[ai_model]
        start_time = time.time()

        try:
            # 実際のAI呼び出し（gemini, qwen等のCLIツール使用）
            if participant.command == "gemini":
                # Gemini CLI呼び出し
                result = await self._run_command(f'gemini --prompt "{prompt}"')
            elif participant.command == "qwen":
                # Qwen CLI呼び出し
                result = await self._run_command(f'qwen -y -p "{prompt}"')
            elif participant.command == "codex":
                # GPT-5/Codex呼び出し
                result = await self._run_command(f'codex exec "{prompt}"')
            elif participant.command == "cursor-agent":
                # Cursor Agent呼び出し
                result = await self._run_command(f'cursor-agent -p "{prompt}"')
            else:
                # Claude（仮想的な処理）
                result = f"[{ai_model.value}] {prompt[:100]}... への応答"

            participant.response_time = time.time() - start_time
            return result

        except Exception as e:
            return f"[{ai_model.value}] エラー: {str(e)}"

    async def _run_command(self, command: str) -> str:
        """非同期でコマンドを実行"""
        loop = asyncio.get_event_loop()

        def run():
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
                return result.stdout if result.returncode == 0 else result.stderr
            except subprocess.TimeoutExpired:
                return "タイムアウト"
            except Exception as e:
                return f"エラー: {str(e)}"

        return await loop.run_in_executor(self.executor, run)

    async def broadcast_message(self, message: Message):
        """全AIにメッセージをブロードキャスト"""
        await self.message_queue.put(message)
        self.message_history.append(message)

        # メッセージの可視化
        print(f"\n🎯 [{message.sender.value}] ({message.message_type})")
        print(f"   {message.content[:200]}...")
        if message.in_reply_to:
            print(f"   ↳ Reply to: {message.in_reply_to[:8]}")

    async def ai_discussion_worker(self, ai_model: AIModel, topic: DiscussionTopic):
        """各AIの議論ワーカー"""
        participant = self.participants[ai_model]

        while participant.active:
            try:
                # メッセージキューから新しいメッセージを取得（非ブロッキング）
                try:
                    recent_message = self.message_queue.get_nowait()

                    # 自分以外のメッセージに反応
                    if recent_message.sender != ai_model:
                        # 専門分野に関連する場合は応答
                        should_respond = any(
                            keyword in recent_message.content.lower() for keyword in participant.expertise
                        )

                        if should_respond or len(self.message_history) % 5 == 0:
                            # プロンプト構築
                            prompt = self._build_response_prompt(ai_model, recent_message, topic)

                            # 並列でAI応答を取得
                            response = await self.call_ai_parallel(ai_model, prompt)

                            # メッセージ作成
                            message = Message(
                                id=self._generate_message_id(),
                                sender=ai_model,
                                content=response,
                                timestamp=datetime.now(),
                                in_reply_to=recent_message.id,
                                message_type=self._determine_message_type(response),
                            )

                            # ブロードキャスト
                            await self.broadcast_message(message)

                except asyncio.QueueEmpty:
                    # キューが空の場合は独自の提案を行う
                    if (
                        len(self.message_history) < 3
                        or (datetime.now() - self.message_history[-1].timestamp).seconds > 10
                    ):
                        prompt = self._build_initial_prompt(ai_model, topic)
                        response = await self.call_ai_parallel(ai_model, prompt)

                        message = Message(
                            id=self._generate_message_id(),
                            sender=ai_model,
                            content=response,
                            timestamp=datetime.now(),
                            message_type="statement",
                        )

                        await self.broadcast_message(message)

                # 短い待機（CPU負荷軽減）
                await asyncio.sleep(0.5)

                # タイムアウトチェック
                if self.start_time and (datetime.now() - self.start_time).seconds > topic.deadline_seconds:
                    participant.active = False

            except Exception as e:
                print(f"❌ [{ai_model.value}] エラー: {str(e)}")
                await asyncio.sleep(1)

    def _build_response_prompt(self, ai_model: AIModel, message: Message, topic: DiscussionTopic) -> str:
        """応答プロンプトの構築"""
        participant = self.participants[ai_model]

        # 最近の議論コンテキスト
        recent_context = "\n".join([f"[{msg.sender.value}]: {msg.content[:100]}" for msg in self.message_history[-5:]])

        return f"""
あなたは{participant.role}として、以下の議論に参加しています。

トピック: {topic.title}
目的: {', '.join(topic.objectives)}

最近の議論:
{recent_context}

直前のメッセージ:
[{message.sender.value}]: {message.content}

あなたの専門分野（{', '.join(participant.expertise)}）の観点から、
簡潔で具体的な意見を述べてください。必要に応じて:
- 賛成/反対を明確に
- 代替案の提示
- 技術的な根拠の提供
- リスクの指摘

回答は200文字以内で簡潔に。
"""

    def _build_initial_prompt(self, ai_model: AIModel, topic: DiscussionTopic) -> str:
        """初期提案プロンプトの構築"""
        participant = self.participants[ai_model]

        return f"""
あなたは{participant.role}として、以下のトピックについて議論します。

トピック: {topic.title}
説明: {topic.description}
目的: {', '.join(topic.objectives)}
制約: {', '.join(topic.constraints)}

あなたの専門分野（{', '.join(participant.expertise)}）から、
最も重要と考える提案や意見を1つ述べてください。

回答は200文字以内で簡潔に。
"""

    def _determine_message_type(self, content: str) -> str:
        """メッセージタイプの判定"""
        content_lower = content.lower()

        if "?" in content:
            return "question"
        elif any(word in content_lower for word in ["賛成", "同意", "agree", "良い"]):
            return "agreement"
        elif any(word in content_lower for word in ["反対", "懸念", "リスク", "問題"]):
            return "objection"
        elif any(word in content_lower for word in ["回答", "答え", "because", "なぜなら"]):
            return "answer"
        else:
            return "statement"

    def _generate_message_id(self) -> str:
        """メッセージIDの生成"""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:8]

    async def run_discussion(self, topic: DiscussionTopic) -> Dict[str, Any]:
        """議論の実行"""
        self.start_time = datetime.now()
        print(f"\n🚀 リアルタイム5AI議論開始: {topic.title}")
        print(f"⏰ 制限時間: {topic.deadline_seconds}秒")
        print("=" * 60)

        # 全AIワーカーを並列起動
        tasks = [
            asyncio.create_task(self.ai_discussion_worker(ai_model, topic)) for ai_model in self.participants.keys()
        ]

        # タイムアウトまたは合意形成まで待機
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=topic.deadline_seconds)
        except asyncio.TimeoutError:
            print("\n⏱️ 議論時間終了")

        # 議論の要約と合意事項の抽出
        summary = self._generate_discussion_summary()

        return {
            "topic": topic.title,
            "duration": (datetime.now() - self.start_time).seconds,
            "message_count": len(self.message_history),
            "participants": [p.model.value for p in self.participants.values()],
            "average_response_time": self._calculate_avg_response_time(),
            "summary": summary,
            "consensus": self._extract_consensus(),
            "messages": [msg.to_dict() for msg in self.message_history],
        }

    def _generate_discussion_summary(self) -> str:
        """議論の要約生成"""
        if not self.message_history:
            return "議論なし"

        # メッセージタイプ別カウント
        type_counts = {}
        for msg in self.message_history:
            type_counts[msg.message_type] = type_counts.get(msg.message_type, 0) + 1

        # 各AIの発言回数
        ai_counts = {}
        for msg in self.message_history:
            ai_counts[msg.sender.value] = ai_counts.get(msg.sender.value, 0) + 1

        summary = f"""
議論統計:
- 総メッセージ数: {len(self.message_history)}
- 発言タイプ: {type_counts}
- AI別発言数: {ai_counts}
- 平均応答時間: {self._calculate_avg_response_time():.2f}秒
"""
        return summary

    def _calculate_avg_response_time(self) -> float:
        """平均応答時間の計算"""
        times = [p.response_time for p in self.participants.values() if p.response_time > 0]
        return sum(times) / len(times) if times else 0.0

    def _extract_consensus(self) -> List[str]:
        """合意事項の抽出"""
        consensus_items = []

        # 賛成メッセージをカウント
        agreements = [msg for msg in self.message_history if msg.message_type == "agreement"]

        if agreements:
            consensus_items.append(f"{len(agreements)}件の合意形成")

        # 反対意見がない提案を合意とみなす
        unopposed_statements = []
        for msg in self.message_history:
            if msg.message_type == "statement":
                # このメッセージへの反対があるかチェック
                objections = [
                    m for m in self.message_history if m.in_reply_to == msg.id and m.message_type == "objection"
                ]
                if not objections:
                    unopposed_statements.append(msg.content[:50])

        if unopposed_statements:
            consensus_items.append(f"反対なし提案: {len(unopposed_statements)}件")

        return consensus_items


# 実行例
async def main():
    """メイン実行関数"""

    # 議論トピックの定義
    topic = DiscussionTopic(
        title="workplace-roleplayの最適なアーキテクチャ選択",
        description="Flask vs FastAPI vs Quartの選択と移行戦略",
        context="現在Flaskで実装されているが、パフォーマンスとスケーラビリティの問題がある",
        objectives=["最適なフレームワークの選択", "段階的移行プランの策定", "リスクの最小化"],
        constraints=["ダウンタイムは最小限に", "既存機能の維持", "3ヶ月以内の完了"],
        deadline_seconds=300,  # 5分の高速議論
    )

    # オーケストレーター初期化
    orchestrator = RealtimeDiscussionOrchestrator()

    # 議論実行
    result = await orchestrator.run_discussion(topic)

    # 結果の保存
    with open("discussion_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("📊 議論完了!")
    print(f"⏱️ 所要時間: {result['duration']}秒")
    print(f"💬 総メッセージ数: {result['message_count']}")
    print(f"⚡ 平均応答時間: {result['average_response_time']:.2f}秒")
    print("\n🤝 合意事項:")
    for item in result["consensus"]:
        print(f"  ✓ {item}")


if __name__ == "__main__":
    # 非同期実行
    asyncio.run(main())
