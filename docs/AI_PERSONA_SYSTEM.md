# AIペルソナシステム ドキュメント

## 概要

AIペルソナシステムは、workplace-roleplayアプリケーションにおいて、よりリアルで多様な職場コミュニケーション練習を実現するための機能です。業界、役職、性格、経験年数などの特性を持つAIペルソナが、シナリオに応じて適切な対話相手となります。

## システムアーキテクチャ

### 1. データベース構造

#### AIPersona（ai_personas）
- **基本情報**: 名前、年齢、性別、ペルソナコード
- **職業情報**: 業界、役職、経験年数、会社規模
- **性格特性**: 性格タイプ、コミュニケーションスタイル、ストレス要因、モチベーション要因
- **背景情報**: 背景ストーリー、現在の課題、目標
- **専門性**: 専門分野、技術スキル、言語パターン

#### PersonaMemory（persona_memories）
- ペルソナの記憶システム
- ユーザーとの過去の対話を記憶
- 重要度スコアによる記憶の優先順位付け
- 自動的な記憶の期限管理

#### PersonaScenarioConfig（persona_scenario_configs）
- シナリオ別のペルソナ設定
- 役割、初期態度、協力レベル
- カスタム台詞や反応パターン

#### UserPersonaInteraction（user_persona_interactions）
- ユーザーとペルソナの対話履歴
- ラポールレベルの追跡
- 感情状態の記録
- スキル実証の記録

### 2. ペルソナの種類

現在実装されている5つの代表的ペルソナ：

1. **佐藤 健一（IT_MANAGER_ANALYTICAL）**
   - IT業界のマネージャー、分析的性格
   - 15年の経験、論理的思考重視

2. **田中 美咲（SALES_SENIOR_EXPRESSIVE）**
   - 営業・販売の先輩社員、表現豊か
   - 8年の経験、関係構築重視

3. **山田 和子（HEALTHCARE_MENTOR_AMIABLE）**
   - 医療・福祉のメンター、協調的
   - 20年の経験、サポート重視

4. **鈴木 大輔（MANUFACTURING_TEAMLEAD_DRIVER）**
   - 製造業のチームリーダー、推進力重視
   - 12年の経験、結果志向

5. **小林 翔太（FINANCE_JUNIOR_DETAIL）**
   - 金融業界の新入社員、細部重視
   - 2年の経験、正確性重視

### 3. 主要コンポーネント

#### PersonaService
- ペルソナの基本的なCRUD操作
- プロンプト生成
- メモリ管理
- 感情状態の管理

#### PersonaScenarioIntegrationService
- シナリオとペルソナのマッチング
- 適合度スコアリング
- 対話記録の管理
- 統計情報の提供

## API仕様

### エンドポイント

#### GET /api/persona-scenarios/suitable-personas/{scenario_id}
シナリオに適したペルソナのリストを取得

**レスポンス例:**
```json
{
  "personas": [
    {
      "persona_code": "IT_MANAGER_ANALYTICAL",
      "name": "佐藤 健一",
      "role": "マネージャー",
      "industry": "IT・ソフトウェア",
      "personality_type": "分析的",
      "description": "45歳のIT・ソフトウェア業界のマネージャー",
      "years_experience": 15
    }
  ],
  "count": 5
}
```

#### POST /api/persona-scenarios/stream
ペルソナベースのシナリオチャットストリーミング

**リクエスト:**
```json
{
  "message": "おはようございます",
  "scenario_id": "scenario1",
  "persona_code": "IT_MANAGER_ANALYTICAL",
  "session_id": "optional_session_id"
}
```

**レスポンス:** Server-Sent Events (SSE) ストリーム

#### GET /api/persona-scenarios/persona-stats/{persona_code}
ペルソナの統計情報を取得

**レスポンス例:**
```json
{
  "total_interactions": 150,
  "unique_users": 25,
  "average_rapport": 0.75,
  "scenario_breakdown": {
    "scenario1": {
      "count": 45,
      "avg_rapport": 0.8
    }
  }
}
```

## フロントエンド統合

### JavaScript統合例

```javascript
// ペルソナシナリオマネージャーの初期化
const manager = new PersonaScenarioManager();

// シナリオに適したペルソナを取得
const { personas } = await manager.getSuitablePersonas('scenario1');

// ペルソナを選択してシナリオを開始
const response = await manager.startPersonaScenarioChat(
  'scenario1', 
  'IT_MANAGER_ANALYTICAL'
);

// メッセージを送信
const reply = await manager.sendMessage('プロジェクトの進捗はいかがですか？');
```

### ストリーミング対応

```javascript
// ストリーミング更新のコールバック設定
manager.setStreamUpdateCallback((content) => {
  // リアルタイムで画面を更新
  updateChatDisplay(content);
});
```

## ペルソナ選択アルゴリズム

### 適合度スコアリング

1. **業界マッチング** (20点)
   - シナリオカテゴリとペルソナ業界の一致

2. **難易度マッチング** (15点)
   - シナリオ難易度とペルソナ経験年数の適合

3. **役職マッチング** (25-30点)
   - シナリオの対話相手設定とペルソナ役職の一致

4. **使用頻度調整** (±10点)
   - 新しいペルソナを優先、使いすぎを抑制

5. **ランダム要素** (±5点)
   - 多様性確保のための微調整

## メモリシステム

### メモリタイプ

- **SHORT_TERM**: 短期記憶（現在のセッション）
- **LONG_TERM**: 長期記憶（重要な情報）
- **EPISODIC**: エピソード記憶（特定の出来事）
- **SEMANTIC**: 意味記憶（一般的な知識）

### 記憶の管理

- 重要度スコアによる優先順位付け
- 有効期限による自動削除
- コンテキストに応じた記憶の検索

## 感情状態システム

### 感情状態の種類

- **NEUTRAL**: 中立
- **HAPPY**: 喜び
- **STRESSED**: ストレス
- **FRUSTRATED**: 苛立ち
- **CONFIDENT**: 自信
- **CONFUSED**: 困惑
- **INTERESTED**: 興味

### 感情の判定

会話履歴から以下の要素を分析：
- ポジティブ/ネガティブキーワード
- ストレス関連語句
- 会話の流れとコンテキスト

## 設定とカスタマイズ

### ペルソナのカスタマイズ

新しいペルソナを追加する場合：

1. `data/personas/`ディレクトリにYAMLファイルを作成
2. 必要な属性を定義（既存ファイルを参考）
3. `load_personas.py`スクリプトを実行

### YAMLファイル例

```yaml
persona_code: "RETAIL_SUPERVISOR_BALANCED"
name: "高橋 太郎"
name_reading: "タカハシ タロウ"
age: 35
gender: "男性"
industry: "RETAIL"
role: "SUPERVISOR"
years_experience: 10
personality_type: "AMIABLE"
communication_style:
  - "親しみやすい話し方"
  - "チームの和を重視"
background_story: "小売業界で10年のキャリアを持つスーパーバイザー..."
```

## パフォーマンス最適化

### キャッシング戦略

- Redisを使用したペルソナ情報のキャッシング
- 頻繁にアクセスされるメモリのキャッシュ
- セッション情報の効率的な管理

### スケーラビリティ

- ペルソナごとの独立したメモリ管理
- 非同期処理によるレスポンス時間の短縮
- データベースインデックスの最適化

## トラブルシューティング

### よくある問題

1. **ペルソナが見つからない**
   - YAMLファイルが正しく配置されているか確認
   - `load_personas.py`を実行してデータベースに同期

2. **メモリが保存されない**
   - ユーザーが認証されているか確認
   - Redisサービスが起動しているか確認

3. **感情状態が適切でない**
   - 会話履歴が十分にあるか確認
   - キーワード辞書の更新を検討

## 今後の拡張計画

1. **多言語対応**
   - 英語、中国語などのペルソナ追加

2. **業界特化型ペルソナ**
   - より専門的な業界知識を持つペルソナ

3. **動的ペルソナ生成**
   - ユーザーのニーズに応じた自動生成

4. **感情認識の高度化**
   - 機械学習による感情分析

5. **ペルソナ間の関係性**
   - ペルソナ同士の相互作用モデル