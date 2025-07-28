"""
AIペルソナシステムのテストスイート
"""
import pytest
from datetime import datetime
from app import app
from models import db, AIPersona, PersonaMemory, UserPersonaInteraction, PersonaIndustry, PersonaRole, PersonaPersonality, EmotionalState
from services.persona_service import PersonaService
from services.persona_scenario_integration import PersonaScenarioIntegrationService


class TestPersonaSystem:
    """ペルソナシステムの基本機能テスト"""
    
    @pytest.fixture
    def client(self):
        """テスト用クライアントのセットアップ"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app.test_client()
            db.drop_all()
    
    @pytest.fixture
    def sample_persona(self):
        """テスト用ペルソナの作成"""
        with app.app_context():
            persona = AIPersona(
                persona_code='TEST_PERSONA_01',
                name='テスト 太郎',
                name_reading='テスト タロウ',
                age=30,
                gender='男性',
                industry=PersonaIndustry.IT,
                role=PersonaRole.SENIOR,
                years_experience=5,
                personality_type=PersonaPersonality.ANALYTICAL,
                communication_style={'formal': 0.8, 'technical': 0.9, 'empathetic': 0.3},
                stress_triggers=['期限', '急いで'],
                motivation_factors=['成功', '学習'],
                background_story='テスト用のペルソナです',
                current_challenges=['新技術への対応', 'チーム管理'],
                goals=['技術向上', 'プロジェクト成功'],
                expertise_areas=['Python', 'データベース'],
                technical_skills=['SQL', 'Docker'],
                speech_patterns=['具体的に言うと', 'データから見ると', '効率的に'],
                is_active=True
            )
            db.session.add(persona)
            db.session.commit()
            return persona
    
    def test_persona_creation(self, client, sample_persona):
        """ペルソナの作成テスト"""
        with app.app_context():
            # ペルソナが正しく作成されているか確認
            persona = AIPersona.query.filter_by(persona_code='TEST_PERSONA_01').first()
            assert persona is not None
            assert persona.name == 'テスト 太郎'
            assert persona.industry == PersonaIndustry.IT
            assert persona.role == PersonaRole.SENIOR
    
    def test_persona_service_prompt_generation(self, client, sample_persona):
        """ペルソナサービスのプロンプト生成テスト"""
        with app.app_context():
            # セッションから再取得してDetachedエラーを回避
            persona = AIPersona.query.filter_by(persona_code='TEST_PERSONA_01').first()
            service = PersonaService()
            
            # テスト用のシナリオコンテキスト
            scenario_context = {
                'title': '会議での意見交換',
                'description': 'チーム会議で新しいプロジェクトについて話し合う',
                'difficulty': 'intermediate'
            }
            
            # プロンプト生成
            prompt = service.create_persona_prompt(
                persona=persona,
                scenario_context=scenario_context,
                user_message='新しいプロジェクトについてどう思いますか？',
                conversation_history=[]
            )
            
            # プロンプトが生成されているか確認
            assert prompt is not None
            assert 'テスト 太郎' in prompt
            assert 'technical' in prompt or 'フォーマル度' in prompt
            assert '新しいプロジェクト' in prompt
    
    def test_memory_system(self, client, sample_persona):
        """メモリシステムのテスト"""
        with app.app_context():
            # テスト用ユーザーを作成
            from models import User
            test_user = User(username='test_user', email='test@example.com')
            test_user.set_password('testpass')
            db.session.add(test_user)
            db.session.commit()
            
            # セッションから再取得してDetachedエラーを回避
            persona = AIPersona.query.filter_by(persona_code='TEST_PERSONA_01').first()
            
            # メモリを作成
            memory = PersonaMemory(
                persona_id=persona.id,
                user_id=test_user.id,
                memory_type='SHORT_TERM',
                content='ユーザーはPythonが得意',
                context_tags=['技術的な会話'],
                importance_score=0.8
            )
            db.session.add(memory)
            db.session.commit()
            
            # メモリが保存されているか確認
            saved_memory = PersonaMemory.query.filter_by(
                persona_id=persona.id,
                user_id=test_user.id
            ).first()
            
            assert saved_memory is not None
            assert saved_memory.content == 'ユーザーはPythonが得意'
            assert saved_memory.importance_score == 0.8
    
    def test_scenario_integration(self, client, sample_persona):
        """シナリオ統合サービスのテスト"""
        with app.app_context():
            # セッションから再取得してDetachedエラーを回避
            persona = AIPersona.query.filter_by(persona_code='TEST_PERSONA_01').first()
            integration_service = PersonaScenarioIntegrationService()
            
            # 適合度スコアの計算テスト
            scenario_data = {
                'category': 'ビジネス',
                'difficulty': 'intermediate',
                'conversation_partner': '先輩社員'
            }
            
            score = integration_service._calculate_persona_scenario_fit(
                persona,
                scenario_data,
                None
            )
            
            # スコアが計算されているか確認
            assert score >= 0
            assert isinstance(score, float)
    
    def test_emotional_state_determination(self, client, sample_persona):
        """感情状態判定のテスト"""
        with app.app_context():
            # セッションから再取得してDetachedエラーを回避
            persona = AIPersona.query.filter_by(persona_code='TEST_PERSONA_01').first()
            integration_service = PersonaScenarioIntegrationService()
            
            # ポジティブな会話履歴
            positive_history = [
                {'role': 'user', 'content': 'ありがとうございます！素晴らしいアイデアですね。'},
                {'role': 'assistant', 'content': 'お役に立てて嬉しいです。'}
            ]
            
            emotional_state = integration_service._determine_emotional_state(
                persona,
                positive_history
            )
            
            # ポジティブな感情状態が判定されるか確認
            assert emotional_state in [EmotionalState.HAPPY, EmotionalState.CONFIDENT]
    
    def test_rapport_calculation(self, client):
        """ラポールレベル計算のテスト"""
        with app.app_context():
            integration_service = PersonaScenarioIntegrationService()
            
            # ラポールレベルの計算
            rapport = integration_service._calculate_rapport_level(
                interaction_count=10,
                positive_interactions=8
            )
            
            # ラポールレベルが適切な範囲か確認
            assert 0.0 <= rapport <= 1.0
            assert rapport > 0.5  # ポジティブな対話が多いので高めのスコア


class TestPersonaAPI:
    """ペルソナAPIエンドポイントのテスト"""
    
    @pytest.fixture
    def client(self):
        """テスト用クライアントのセットアップ"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        
        with app.app_context():
            db.create_all()
            self._setup_test_data()
            yield app.test_client()
            db.drop_all()
    
    def _setup_test_data(self):
        """テスト用データのセットアップ"""
        # テスト用ペルソナを作成
        personas = [
            AIPersona(
                persona_code='TEST_IT_MANAGER',
                name='テストITマネージャー',
                industry=PersonaIndustry.IT,
                role=PersonaRole.MANAGER,
                years_experience=10,
                personality_type=PersonaPersonality.ANALYTICAL,
                is_active=True
            ),
            AIPersona(
                persona_code='TEST_SALES_SENIOR',
                name='テスト営業先輩',
                industry=PersonaIndustry.SALES,
                role=PersonaRole.SENIOR,
                years_experience=5,
                personality_type=PersonaPersonality.EXPRESSIVE,
                is_active=True
            )
        ]
        
        for persona in personas:
            db.session.add(persona)
        db.session.commit()
    
    def test_get_suitable_personas(self, client):
        """適切なペルソナ取得APIのテスト"""
        response = client.get('/api/persona-scenarios/suitable-personas/scenario1')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'personas' in data
        assert 'count' in data
        assert isinstance(data['personas'], list)
    
    def test_persona_stats_api(self, client):
        """ペルソナ統計APIのテスト"""
        response = client.get('/api/persona-scenarios/persona-stats/TEST_IT_MANAGER')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'total_interactions' in data
        assert 'unique_users' in data
        assert 'average_rapport' in data


class TestPersonaDataIntegrity:
    """ペルソナデータの整合性テスト"""
    
    @pytest.fixture
    def client(self):
        """本番データベースのペルソナをテスト"""
        with app.app_context():
            yield app.test_client()
    
    def test_loaded_personas_integrity(self, client):
        """読み込まれたペルソナの整合性チェック"""
        with app.app_context():
            # すべてのアクティブなペルソナを取得
            personas = AIPersona.query.filter_by(is_active=True).all()
            
            # 5つのペルソナが存在することを確認
            assert len(personas) >= 5
            
            # 各ペルソナの必須フィールドをチェック
            for persona in personas:
                assert persona.persona_code is not None
                assert persona.name is not None
                assert persona.industry is not None
                assert persona.role is not None
                assert persona.personality_type is not None
                assert persona.years_experience >= 0
                
                # コミュニケーションスタイルが辞書であることを確認
                if persona.communication_style:
                    assert isinstance(persona.communication_style, dict)
    
    def test_persona_enum_values(self, client):
        """Enumの値が正しいことを確認"""
        with app.app_context():
            # PersonaIndustryの値チェック
            assert PersonaIndustry.IT.value == 'IT・ソフトウェア'
            assert PersonaIndustry.SALES.value == '営業・販売'
            assert PersonaIndustry.HEALTHCARE.value == '医療・福祉'
            assert PersonaIndustry.MANUFACTURING.value == '製造業'
            assert PersonaIndustry.FINANCE.value == '金融'
            
            # PersonaRoleの値チェック
            assert PersonaRole.JUNIOR.value == '新入社員'
            assert PersonaRole.SENIOR.value == '先輩社員'
            assert PersonaRole.TEAMLEAD.value == 'チームリーダー'
            assert PersonaRole.MANAGER.value == 'マネージャー'
            assert PersonaRole.MENTOR.value == 'メンター'
            
            # PersonaPersonalityの値チェック
            assert PersonaPersonality.ANALYTICAL.value == '分析的'
            assert PersonaPersonality.DRIVER.value == '推進力重視'
            assert PersonaPersonality.AMIABLE.value == '協調的'
            assert PersonaPersonality.EXPRESSIVE.value == '表現豊か'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])