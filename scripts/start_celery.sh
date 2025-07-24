#!/bin/bash
# Celeryワーカー起動スクリプト

# カラー出力用の設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Celery Worker 起動スクリプト ===${NC}"

# 環境変数の読み込み
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo -e "${GREEN}✅ 環境変数を読み込みました${NC}"
else
    echo -e "${YELLOW}⚠️  .envファイルが見つかりません${NC}"
fi

# Redisの起動確認
echo -e "\n${YELLOW}Redis接続を確認中...${NC}"
redis-cli ping > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Redisが起動しています${NC}"
else
    echo -e "${RED}❌ Redisが起動していません${NC}"
    echo -e "${YELLOW}以下のコマンドでRedisを起動してください:${NC}"
    echo "  brew services start redis  # macOS"
    echo "  sudo systemctl start redis  # Linux"
    echo "  docker run -d -p 6379:6379 redis  # Docker"
    exit 1
fi

# 既存のCeleryプロセスを停止
echo -e "\n${YELLOW}既存のCeleryプロセスを確認中...${NC}"
pgrep -f "celery.*workplace_roleplay" > /dev/null
if [ $? -eq 0 ]; then
    echo -e "${YELLOW}既存のCeleryプロセスを停止中...${NC}"
    pkill -f "celery.*workplace_roleplay"
    sleep 2
fi

# ログディレクトリの作成
mkdir -p logs/celery

# Celeryワーカーの起動
echo -e "\n${GREEN}Celeryワーカーを起動中...${NC}"

# 開発環境用の設定
if [ "$FLASK_ENV" = "development" ]; then
    echo -e "${YELLOW}開発モードで起動します${NC}"
    celery -A celery_app worker \
        --loglevel=info \
        --concurrency=4 \
        --queues=default,llm,feedback,analytics \
        --logfile=logs/celery/worker.log \
        &
else
    echo -e "${YELLOW}本番モードで起動します${NC}"
    celery -A celery_app worker \
        --loglevel=warning \
        --concurrency=8 \
        --queues=default,llm,feedback,analytics \
        --logfile=logs/celery/worker.log \
        --detach
fi

# プロセスの確認
sleep 3
pgrep -f "celery.*workplace_roleplay" > /dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Celeryワーカーが正常に起動しました${NC}"
    echo -e "\n${YELLOW}ログファイル:${NC} logs/celery/worker.log"
    echo -e "${YELLOW}ログ確認:${NC} tail -f logs/celery/worker.log"
    echo -e "${YELLOW}停止方法:${NC} pkill -f 'celery.*workplace_roleplay'"
else
    echo -e "${RED}❌ Celeryワーカーの起動に失敗しました${NC}"
    echo -e "${YELLOW}ログを確認してください:${NC} cat logs/celery/worker.log"
    exit 1
fi

# Flower（Celery監視ツール）の起動オプション
echo -e "\n${YELLOW}Celery Flower（監視ツール）を起動しますか？ [y/N]${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "${GREEN}Flowerを起動中...${NC}"
    celery -A celery_app flower --port=5555 &
    echo -e "${GREEN}✅ Flowerが起動しました${NC}"
    echo -e "${YELLOW}アクセスURL:${NC} http://localhost:5555"
fi

echo -e "\n${GREEN}=== 起動完了 ===${NC}"