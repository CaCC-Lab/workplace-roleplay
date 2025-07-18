"""
データベースモデル定義

PostgreSQLを使用してユーザーデータ、学習履歴、会話ログを永続化
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import enum
import uuid

db = SQLAlchemy()


class DifficultyLevel(enum.Enum):
    """シナリオ難易度"""
    BEGINNER = "初級"
    INTERMEDIATE = "中級"
    ADVANCED = "上級"
    UNKNOWN = "不明"


class SessionType(enum.Enum):
    """練習セッションの種類"""
    SCENARIO = "scenario"      # シナリオモード
    FREE_TALK = "free_talk"    # 雑談モード
    WATCH = "watch"            # 観戦モード


class User(UserMixin, db.Model):
    """ユーザーアカウント情報"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    
    # リレーションシップ
    sessions = db.relationship('PracticeSession', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """パスワードをハッシュ化して保存"""
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """パスワードを検証"""
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        return bcrypt.check_password_hash(self.password_hash, password)


class Scenario(db.Model):
    """シナリオ基本情報（YAMLファイルとの対応）"""
    __tablename__ = 'scenarios'
    
    id = db.Column(db.Integer, primary_key=True)
    yaml_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    difficulty = db.Column(
        db.Enum(DifficultyLevel, 
                name="difficulty_level_enum",
                values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=DifficultyLevel.UNKNOWN.value,
        default=DifficultyLevel.UNKNOWN
    )
    category = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # リレーションシップ
    sessions = db.relationship('PracticeSession', back_populates='scenario', lazy='dynamic')
    
    def __repr__(self):
        return f'<Scenario {self.title}>'


class PracticeSession(db.Model):
    """練習セッション（一回の練習単位）"""
    __tablename__ = 'practice_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_uuid = db.Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey('scenarios.id'), nullable=True, index=True)
    session_type = db.Column(db.Enum(SessionType), nullable=False)
    ai_model = db.Column(db.String(50), nullable=True)  # 使用したAIモデル
    started_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    ended_at = db.Column(db.DateTime(timezone=True), nullable=True)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    
    # リレーションシップ
    user = db.relationship('User', back_populates='sessions')
    scenario = db.relationship('Scenario', back_populates='sessions')
    logs = db.relationship('ConversationLog', back_populates='session', lazy='dynamic', cascade="all, delete-orphan", order_by="ConversationLog.timestamp")
    analysis = db.relationship('StrengthAnalysis', back_populates='session', uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<PracticeSession {self.session_uuid}>'


class ConversationLog(db.Model):
    """会話ログ（各発言の記録）"""
    __tablename__ = 'conversation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('practice_sessions.id'), nullable=False, index=True)
    speaker = db.Column(db.String(50), nullable=False)  # 'user', 'ai', 'ai_model1', 'ai_model2' など
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')  # 'text', 'system', 'feedback'
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # オプション：音声データのパスやIDを保存する場合
    audio_data_id = db.Column(db.String(100), nullable=True)
    
    # リレーションシップ
    session = db.relationship('PracticeSession', back_populates='logs')
    
    def __repr__(self):
        return f'<ConversationLog {self.speaker}: {self.message[:50]}...>'


class StrengthAnalysis(db.Model):
    """強み分析結果"""
    __tablename__ = 'strength_analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('practice_sessions.id'), unique=True, nullable=False)
    
    # 6つのスキル項目（0.0 - 1.0）
    empathy = db.Column(db.Float, nullable=False)
    clarity = db.Column(db.Float, nullable=False)
    listening = db.Column(db.Float, nullable=False)
    problem_solving = db.Column(db.Float, nullable=False)
    assertiveness = db.Column(db.Float, nullable=False)
    flexibility = db.Column(db.Float, nullable=False)
    
    # フィードバックと評価
    feedback_text = db.Column(db.Text, nullable=True)
    overall_score = db.Column(db.Float, nullable=True)
    improvement_suggestions = db.Column(db.JSON, nullable=True)  # JSON形式で改善提案を保存
    
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # リレーションシップ
    session = db.relationship('PracticeSession', back_populates='analysis')
    
    def __repr__(self):
        return f'<StrengthAnalysis for session {self.session_id}>'
    
    def validate_skill_scores(self):
        """スキルスコアが0.0から1.0の範囲内であることを検証"""
        skills = {
            'empathy': self.empathy,
            'clarity': self.clarity,
            'listening': self.listening,
            'problem_solving': self.problem_solving,
            'assertiveness': self.assertiveness,
            'flexibility': self.flexibility
        }
        
        for skill_name, score in skills.items():
            if score is not None and not (0.0 <= score <= 1.0):
                raise ValueError(f"スキル '{skill_name}' の値が範囲外です: {score} (0.0-1.0の範囲である必要があります)")
    
    def get_top_strengths(self, top_n=3):
        """上位の強みを取得"""
        strengths = {
            'empathy': self.empathy,
            'clarity': self.clarity,
            'listening': self.listening,
            'problem_solving': self.problem_solving,
            'assertiveness': self.assertiveness,
            'flexibility': self.flexibility
        }
        return sorted(strengths.items(), key=lambda x: x[1], reverse=True)[:top_n]


# インデックスの追加（パフォーマンス最適化）
from sqlalchemy import Index

# 複合インデックス
Index('idx_session_user_date', PracticeSession.user_id, PracticeSession.started_at)
Index('idx_log_session_timestamp', ConversationLog.session_id, ConversationLog.timestamp)