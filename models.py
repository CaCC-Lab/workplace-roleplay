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


class Achievement(db.Model):
    """アチーブメント（達成記録）"""
    __tablename__ = 'achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(50), nullable=True)  # アイコン名またはUnicode絵文字
    category = db.Column(db.String(50), nullable=False)  # 'practice', 'consistency', 'skill', 'special'
    threshold_type = db.Column(db.String(50), nullable=False)  # 'count', 'streak', 'score', 'custom'
    threshold_value = db.Column(db.Integer, nullable=False)
    points = db.Column(db.Integer, default=10, nullable=False)  # ポイント報酬
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # リレーションシップ
    user_achievements = db.relationship('UserAchievement', back_populates='achievement', lazy='dynamic')
    
    def __repr__(self):
        return f'<Achievement {self.name}>'


class UserAchievement(db.Model):
    """ユーザーのアチーブメント獲得記録"""
    __tablename__ = 'user_achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'), nullable=False, index=True)
    unlocked_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    progress = db.Column(db.Integer, default=0, nullable=False)  # 進捗（例：3/5回完了）
    
    # リレーションシップ
    user = db.relationship('User', backref=db.backref('achievements', lazy='dynamic'))
    achievement = db.relationship('Achievement', back_populates='user_achievements')
    
    # 複合ユニーク制約（同じアチーブメントを複数回獲得しない）
    __table_args__ = (
        db.UniqueConstraint('user_id', 'achievement_id', name='_user_achievement_uc'),
    )
    
    def __repr__(self):
        return f'<UserAchievement {self.user_id}:{self.achievement_id}>'


class StrengthAnalysisResult(db.Model):
    """強み分析結果（新形式）"""
    __tablename__ = 'strength_analysis_results'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('practice_sessions.id'))
    task_id = db.Column(db.String(100))  # Celeryタスクid
    analysis_type = db.Column(db.String(50))  # 'chat', 'scenario'
    
    # 分析結果
    skill_scores = db.Column(db.JSON)  # {'empathy': 4.2, 'clarity': 3.8, ...}
    overall_score = db.Column(db.Float)
    top_strengths = db.Column(db.JSON)  # ['empathy', 'active_listening', ...]
    encouragement_messages = db.Column(db.JSON)  # メッセージのリスト
    raw_analysis = db.Column(db.Text)  # LLMからの生の分析結果
    
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # リレーション
    user = db.relationship('User', backref='strength_analysis_results')
    session = db.relationship('PracticeSession', backref='strength_analysis_results')
    
    def __repr__(self):
        return f'<StrengthAnalysisResult {self.id} - User {self.user_id}>'


class UserPreferences(db.Model):
    """ユーザー設定"""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    
    # 表示設定
    theme = db.Column(db.String(20), default='light', nullable=False)  # 'light', 'dark', 'auto'
    font_size = db.Column(db.String(20), default='medium', nullable=False)  # 'small', 'medium', 'large'
    language = db.Column(db.String(10), default='ja', nullable=False)
    
    # 音声設定
    voice_enabled = db.Column(db.Boolean, default=True, nullable=False)
    voice_speed = db.Column(db.Float, default=1.0, nullable=False)  # 0.5-2.0
    voice_pitch = db.Column(db.Float, default=1.0, nullable=False)  # 0.5-2.0
    voice_volume = db.Column(db.Float, default=0.8, nullable=False)  # 0.0-1.0
    
    # リラックス機能設定
    breathing_guide_enabled = db.Column(db.Boolean, default=True, nullable=False)
    breathing_duration = db.Column(db.Integer, default=60, nullable=False)  # 秒単位
    ambient_sound_enabled = db.Column(db.Boolean, default=False, nullable=False)
    ambient_sound_type = db.Column(db.String(50), default='nature', nullable=True)
    
    # 通知設定
    achievement_notifications = db.Column(db.Boolean, default=True, nullable=False)
    practice_reminders = db.Column(db.Boolean, default=False, nullable=False)
    reminder_time = db.Column(db.Time, nullable=True)  # リマインダーの時刻
    
    # その他の設定
    show_encouragement = db.Column(db.Boolean, default=True, nullable=False)  # 励ましメッセージ表示
    difficulty_preference = db.Column(db.String(20), default='auto', nullable=False)  # 'easy', 'normal', 'hard', 'auto'
    
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    
    # リレーションシップ
    user = db.relationship('User', backref=db.backref('preferences', uselist=False))
    
    def __repr__(self):
        return f'<UserPreferences for user {self.user_id}>'


# インデックスの追加（パフォーマンス最適化）
from sqlalchemy import Index

# 複合インデックス
Index('idx_session_user_date', PracticeSession.user_id, PracticeSession.started_at)
Index('idx_log_session_timestamp', ConversationLog.session_id, ConversationLog.timestamp)