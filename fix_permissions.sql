-- データベースに接続して実行: psql -U postgres -d workplace_roleplay_db

-- postgresユーザーにすべての権限を付与
GRANT ALL PRIVILEGES ON DATABASE workplace_roleplay_db TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA public TO postgres;

-- 今後作成されるテーブルにも自動的に権限を付与
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;