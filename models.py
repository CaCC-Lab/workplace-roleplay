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


# ========== AI PERSONA MODELS ==========

class PersonaIndustry(enum.Enum):
    """業界分類"""
    IT = "IT・ソフトウェア"
    SALES = "営業・販売"
    MANUFACTURING = "製造業"
    HEALTHCARE = "医療・福祉"
    EDUCATION = "教育"
    FINANCE = "金融"
    RETAIL = "小売・サービス"
    CONSULTING = "コンサルティング"
    GOVERNMENT = "公務員・行政"
    CREATIVE = "クリエイティブ・メディア"


class PersonaRole(enum.Enum):
    """役職・ポジション"""
    JUNIOR = "新入社員"
    SENIOR = "先輩社員"
    TEAM_LEAD = "チームリーダー"
    MANAGER = "マネージャー"
    EXECUTIVE = "役員"
    CLIENT = "クライアント"
    COLLEAGUE = "同僚"
    SUBORDINATE = "部下"
    MENTOR = "メンター"
    HR = "人事担当"


class PersonaPersonality(enum.Enum):
    """性格タイプ"""
    ANALYTICAL = "分析的"
    DRIVER = "推進力重視"
    AMIABLE = "協調的"
    EXPRESSIVE = "表現豊か"
    DETAIL_ORIENTED = "細部重視"
    BIG_PICTURE = "全体俯瞰"
    INNOVATIVE = "革新的"
    TRADITIONAL = "伝統重視"


class EmotionalState(enum.Enum):
    """感情状態"""
    NEUTRAL = "中立"
    HAPPY = "喜び"
    STRESSED = "ストレス"
    FRUSTRATED = "フラストレーション"
    EXCITED = "興奮"
    CONCERNED = "懸念"
    CONFIDENT = "自信"
    UNCERTAIN = "不安"
    SATISFIED = "満足"
    DISAPPOINTED = "失望"


class AIPersona(db.Model):
    """AIペルソナプロファイル"""
    __tablename__ = 'ai_personas'
    
    id = db.Column(db.Integer, primary_key=True)
    persona_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    name_reading = db.Column(db.String(100))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    
    # 業界・役職情報
    industry = db.Column(db.Enum(PersonaIndustry), nullable=False)
    role = db.Column(db.Enum(PersonaRole), nullable=False)
    years_experience = db.Column(db.Integer, default=5)
    company_size = db.Column(db.String(50))
    
    # 性格・行動特性
    personality_type = db.Column(db.Enum(PersonaPersonality), nullable=False)
    communication_style = db.Column(db.JSON)
    stress_triggers = db.Column(db.JSON)
    motivation_factors = db.Column(db.JSON)
    
    # 背景ストーリー
    background_story = db.Column(db.Text)
    current_challenges = db.Column(db.JSON)
    goals = db.Column(db.JSON)
    
    # 専門知識・スキル
    expertise_areas = db.Column(db.JSON)
    technical_skills = db.Column(db.JSON)
    soft_skills = db.Column(db.JSON)
    
    # 会話特性
    speech_patterns = db.Column(db.JSON)
    vocabulary_level = db.Column(db.String(20), default="professional")
    response_speed = db.Column(db.String(20), default="moderate")
    humor_level = db.Column(db.Float, default=0.3)
    
    # メタ情報
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    
    # リレーションシップ
    memories = db.relationship('PersonaMemory', back_populates='persona', lazy='dynamic', cascade="all, delete-orphan")
    scenario_configs = db.relationship('PersonaScenarioConfig', back_populates='persona', lazy='dynamic', cascade="all, delete-orphan")
    interactions = db.relationship('UserPersonaInteraction', back_populates='persona', lazy='dynamic')
    
    def __repr__(self):
        return f'<AIPersona {self.name} ({self.persona_code})>'
    
    def get_current_emotional_state(self, context=None):
        """現在の感情状態を取得（コンテキストに基づいて動的に決定）"""
        if not context:
            return EmotionalState.NEUTRAL
        return EmotionalState.NEUTRAL


class PersonaMemory(db.Model):
    """ペルソナの記憶・コンテキスト管理"""
    __tablename__ = 'persona_memories'
    
    id = db.Column(db.Integer, primary_key=True)
    persona_id = db.Column(db.Integer, db.ForeignKey('ai_personas.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('practice_sessions.id'))
    
    # 記憶の種類と内容
    memory_type = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    importance_score = db.Column(db.Float, default=0.5)
    
    # コンテキスト情報
    context_tags = db.Column(db.JSON)
    related_entities = db.Column(db.JSON)
    
    # 時系列管理
    occurred_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    expires_at = db.Column(db.DateTime(timezone=True))
    access_count = db.Column(db.Integer, default=0)
    last_accessed = db.Column(db.DateTime(timezone=True))
    
    # リレーションシップ
    persona = db.relationship('AIPersona', back_populates='memories')
    user = db.relationship('User', backref='persona_memories')
    session = db.relationship('PracticeSession', backref='persona_memories')
    
    def __repr__(self):
        return f'<PersonaMemory {self.memory_type}: {self.content[:50]}...>'


class PersonaScenarioConfig(db.Model):
    """ペルソナのシナリオ別設定"""
    __tablename__ = 'persona_scenario_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    persona_id = db.Column(db.Integer, db.ForeignKey('ai_personas.id'), nullable=False, index=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey('scenarios.id'), nullable=False, index=True)
    
    # シナリオでの役割と態度
    scenario_role = db.Column(db.String(100))
    initial_attitude = db.Column(db.String(50))
    cooperation_level = db.Column(db.Float, default=0.7)
    
    # シナリオ固有の設定
    scenario_goals = db.Column(db.JSON)
    hidden_agenda = db.Column(db.Text)
    trigger_points = db.Column(db.JSON)
    
    # 難易度調整
    difficulty_modifier = db.Column(db.Float, default=1.0)
    hint_availability = db.Column(db.Boolean, default=True)
    
    # カスタム台詞・反応
    custom_greetings = db.Column(db.JSON)
    custom_responses = db.Column(db.JSON)
    
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # リレーションシップ
    persona = db.relationship('AIPersona', back_populates='scenario_configs')
    scenario = db.relationship('Scenario', backref='persona_configs')
    
    # 複合ユニーク制約
    __table_args__ = (
        db.UniqueConstraint('persona_id', 'scenario_id', name='_persona_scenario_uc'),
    )
    
    def __repr__(self):
        return f'<PersonaScenarioConfig {self.persona_id}:{self.scenario_id}>'


class UserPersonaInteraction(db.Model):
    """ユーザーとペルソナの相互作用履歴"""
    __tablename__ = 'user_persona_interactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    persona_id = db.Column(db.Integer, db.ForeignKey('ai_personas.id'), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('practice_sessions.id'), nullable=False)
    
    # 相互作用の評価
    rapport_level = db.Column(db.Float, default=0.5)
    interaction_quality = db.Column(db.Float)
    emotional_trajectory = db.Column(db.JSON)
    
    # 重要なイベント
    key_moments = db.Column(db.JSON)
    breakthroughs = db.Column(db.JSON)
    conflicts = db.Column(db.JSON)
    
    # 学習成果
    skills_demonstrated = db.Column(db.JSON)
    areas_for_improvement = db.Column(db.JSON)
    
    # 統計情報
    total_exchanges = db.Column(db.Integer, default=0)
    user_word_count = db.Column(db.Integer, default=0)
    persona_word_count = db.Column(db.Integer, default=0)
    session_duration = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # リレーションシップ
    user = db.relationship('User', backref='persona_interactions')
    persona = db.relationship('AIPersona', back_populates='interactions')
    session = db.relationship('PracticeSession', backref='persona_interaction')
    
    def __repr__(self):
        return f'<UserPersonaInteraction User:{self.user_id} Persona:{self.persona_id}>'


# ペルソナ関連インデックス
Index('idx_persona_industry_role', AIPersona.industry, AIPersona.role)
Index('idx_persona_active', AIPersona.is_active)
Index('idx_memory_persona_user', PersonaMemory.persona_id, PersonaMemory.user_id)
Index('idx_memory_type_importance', PersonaMemory.memory_type, PersonaMemory.importance_score)
Index('idx_interaction_user_rapport', UserPersonaInteraction.user_id, UserPersonaInteraction.rapport_level)