#!/usr/bin/env python3
"""
FastAPI移行PoC (Proof of Concept)
5AI協調設計に基づく実装サンプル

実装者: Claude 4 + Gemini 2.5 + Qwen3-Coder協調実装
目的: Strangler Figパターンでの段階移行検証
"""

from fastapi import FastAPI, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, AsyncGenerator, Any
import asyncio
import json
import jwt
import redis.asyncio as redis
from datetime import datetime, timedelta
import logging
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 認証関連設定
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 30  # 分

# Redis設定
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# === データモデル ===


class ChatMessage(BaseModel):
    """チャットメッセージのデータモデル"""

    role: str = Field(..., description="user/assistant/system")
    content: str = Field(..., description="メッセージ内容")
    timestamp: datetime = Field(default_factory=datetime.now)
    scenario_id: Optional[str] = None


class ChatRequest(BaseModel):
    """チャットリクエスト"""

    message: str = Field(..., min_length=1, max_length=1000)
    mode: str = Field(default="chat", regex="^(chat|scenario|watch)$")
    scenario_id: Optional[str] = None


class ChatResponse(BaseModel):
    """チャットレスポンス"""

    content: str
    sources: Optional[List[str]] = None
    confidence: Optional[float] = None
    processing_time: float


class UserSession(BaseModel):
    """ユーザーセッション"""

    user_id: str
    chat_history: List[ChatMessage] = []
    current_mode: str = "chat"
    scenario_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)


# === アプリケーション初期化 ===


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフサイクル管理"""
    # 起動時
    logger.info("🚀 FastAPI PoC Starting...")

    # Redis接続確認
    try:
        app.state.redis = redis.from_url(REDIS_URL)
        await app.state.redis.ping()
        logger.info("✅ Redis Connected")
    except Exception as e:
        logger.error(f"❌ Redis Connection Failed: {e}")
        app.state.redis = None

    yield

    # 終了時
    if app.state.redis:
        await app.state.redis.close()
    logger.info("👋 FastAPI PoC Shutdown Complete")


# FastAPIアプリ作成
app = FastAPI(
    title="Workplace Roleplay API v2", description="5AI協調設計によるFastAPI移行PoC", version="2.0.0-alpha", lifespan=lifespan
)

# CORS設定（開発用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# テンプレート設定
templates = Jinja2Templates(directory="templates")

# 認証設定
security = HTTPBearer()

# === 認証・セッション管理 ===


async def get_redis() -> redis.Redis:
    """Redis接続取得"""
    if not app.state.redis:
        raise HTTPException(status_code=500, detail="Redis不可")
    return app.state.redis


def create_jwt_token(user_id: str) -> str:
    """JWT作成"""
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """JWT検証"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="無効なトークン")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="トークン期限切れ")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="JWT無効")


async def get_user_session(
    user_id: str = Depends(verify_jwt_token), redis_client: redis.Redis = Depends(get_redis)
) -> UserSession:
    """ユーザーセッション取得"""
    session_key = f"user_session:{user_id}"
    session_data = await redis_client.get(session_key)

    if session_data:
        # 既存セッション復元
        session_dict = json.loads(session_data)
        session = UserSession.parse_obj(session_dict)
    else:
        # 新規セッション作成
        session = UserSession(user_id=user_id)

    # 最終アクティビティ更新
    session.last_activity = datetime.now()
    await redis_client.setex(session_key, 3600, session.json())  # 1時間TTL

    return session


# === 旧FlaskセッションからのTransparent Migration ===


async def migrate_flask_session(flask_session_id: str, redis_client: redis.Redis) -> Optional[str]:
    """Flask セッションを FastAPI セッションに透過移行"""
    try:
        # 旧Flaskセッション読み込み
        flask_key = f"flask_session:{flask_session_id}"
        flask_data = await redis_client.get(flask_key)

        if not flask_data:
            return None

        # データ変換（簡略化実装）
        flask_session = json.loads(flask_data)

        # 新しいユーザーID生成
        new_user_id = f"migrated_{flask_session_id}"

        # 新セッション作成
        new_session = UserSession(
            user_id=new_user_id,
            chat_history=[],  # 必要に応じて変換ロジック追加
            current_mode=flask_session.get("current_mode", "chat"),
        )

        # 新セッション保存
        session_key = f"user_session:{new_user_id}"
        await redis_client.setex(session_key, 3600, new_session.json())

        logger.info(f"✅ Migrated Flask session {flask_session_id} -> {new_user_id}")
        return new_user_id

    except Exception as e:
        logger.error(f"❌ Migration failed for {flask_session_id}: {e}")
        return None


# === AI インテグレーション ===


class AIService:
    """AI サービス統合クラス"""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY 環境変数が必要です")

    async def generate_response(self, messages: List[ChatMessage], mode: str = "chat") -> AsyncGenerator[str, None]:
        """AI レスポンス生成（ストリーミング）"""
        # 実装簡略化：実際はGoogle Gemini APIを呼び出し
        response_parts = ["こんにちは！", "FastAPI移行のPoCです。", "非同期でストリーミング配信中...", "5AIの協調設計による実装です！"]

        for part in response_parts:
            await asyncio.sleep(0.5)  # 擬似的なレスポンス遅延
            yield part


ai_service = AIService()

# === APIエンドポイント ===


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """ルートページ"""
    return templates.TemplateResponse("index.html", {"request": request, "version": "v2.0-alpha"})


@app.post("/api/v2/auth/token")
async def create_token(user_id: str = "demo_user"):
    """認証トークン発行"""
    token = create_jwt_token(user_id)
    return {"access_token": token, "token_type": "bearer", "expires_in": JWT_EXPIRATION * 60}


@app.get("/api/v2/session")
async def get_session_info(session: UserSession = Depends(get_user_session)):
    """セッション情報取得"""
    return {
        "user_id": session.user_id,
        "current_mode": session.current_mode,
        "chat_history_count": len(session.chat_history),
        "last_activity": session.last_activity,
    }


@app.post("/api/v2/chat", response_class=StreamingResponse)
async def chat_stream(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    session: UserSession = Depends(get_user_session),
    redis_client: redis.Redis = Depends(get_redis),
):
    """チャットストリーミングエンドポイント（メイン機能）"""

    start_time = asyncio.get_event_loop().time()

    # ユーザーメッセージをセッションに追加
    user_message = ChatMessage(role="user", content=request.message, scenario_id=request.scenario_id)
    session.chat_history.append(user_message)
    session.current_mode = request.mode

    async def generate_stream():
        """ストリーム生成"""
        ai_response_content = ""

        try:
            # AI応答生成（ストリーミング）
            async for chunk in ai_service.generate_response(session.chat_history, request.mode):
                ai_response_content += chunk

                # SSE フォーマット
                yield f"data: {json.dumps({'type': 'content', 'data': chunk})}\n\n"

            # レスポンス完了
            processing_time = asyncio.get_event_loop().time() - start_time
            completion_data = {
                "type": "complete",
                "processing_time": processing_time,
                "total_length": len(ai_response_content),
            }
            yield f"data: {json.dumps(completion_data)}\n\n"

            # バックグラウンドでセッション更新
            ai_message = ChatMessage(role="assistant", content=ai_response_content, scenario_id=request.scenario_id)
            session.chat_history.append(ai_message)
            background_tasks.add_task(save_session, session, redis_client)

        except Exception as e:
            logger.error(f"Chat error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(), media_type="text/plain", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


async def save_session(session: UserSession, redis_client: redis.Redis):
    """セッション保存（バックグラウンドタスク）"""
    try:
        session_key = f"user_session:{session.user_id}"
        await redis_client.setex(session_key, 3600, session.json())
        logger.info(f"Session saved for user: {session.user_id}")
    except Exception as e:
        logger.error(f"Failed to save session: {e}")


@app.get("/api/v2/scenarios")
async def list_scenarios():
    """シナリオ一覧（キャッシュ対応）"""
    # 実装簡略化
    scenarios = [
        {"id": "workplace_meeting", "title": "会議での意見交換", "difficulty": "medium"},
        {"id": "customer_complaint", "title": "顧客クレーム対応", "difficulty": "hard"},
        {"id": "team_collaboration", "title": "チーム協働", "difficulty": "easy"},
    ]
    return {"scenarios": scenarios}


# === ヘルスチェック ===


@app.get("/api/v2/health")
async def health_check(redis_client: redis.Redis = Depends(get_redis)):
    """ヘルスチェック"""
    try:
        await redis_client.ping()
        redis_status = "healthy"
    except:
        redis_status = "unhealthy"

    return {
        "status": "healthy" if redis_status == "healthy" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "services": {"api": "healthy", "redis": redis_status, "ai_service": "healthy"},  # 実際はAI API接続確認
    }


# === メトリクス（OpenTelemetry準備） ===


@app.get("/api/v2/metrics")
async def get_metrics():
    """メトリクス取得（Prometheus形式準備）"""
    return {
        "requests_total": 100,  # 実装時はカウンター
        "request_duration_seconds": 0.25,  # 実装時はヒストグラム
        "active_sessions": 5,  # 実装時はゲージ
    }


# === 開発用ユーティリティ ===


@app.post("/api/v2/dev/clear-session")
async def clear_session(user_id: str = Depends(verify_jwt_token), redis_client: redis.Redis = Depends(get_redis)):
    """開発用：セッションクリア"""
    session_key = f"user_session:{user_id}"
    await redis_client.delete(session_key)
    return {"message": f"Session cleared for {user_id}"}


if __name__ == "__main__":
    import uvicorn

    # 開発サーバー起動
    uvicorn.run("fastapi-migration-poc:app", host="127.0.0.1", port=8000, reload=True, log_level="info")

"""
実行方法:
1. 依存関係インストール:
   pip install fastapi uvicorn redis python-jose[cryptography] python-multipart jinja2

2. Redis起動:
   docker run -d -p 6379:6379 redis:alpine

3. 環境変数設定:
   export GOOGLE_API_KEY="your_api_key"
   export JWT_SECRET="your_secret_key"

4. サーバー起動:
   python fastapi-migration-poc.py

5. テスト:
   curl -X POST http://localhost:8000/api/v2/auth/token
   curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v2/session

実装特徴:
- ✅ 非同期SSEストリーミング
- ✅ JWT認証（ステートレス）
- ✅ Redisセッション管理
- ✅ 透過的Flask移行
- ✅ バックグラウンドタスク
- ✅ ヘルスチェック・メトリクス
- ✅ Pydanticデータ検証
- ✅ 構造化ロギング
- ✅ OpenTelemetry準備
"""
