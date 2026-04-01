# 実装計画: ゲーミフィケーション機能

## 概要

既存のFlaskアプリケーション（Blueprint + サービス層パターン）に、ゲーミフィケーション要素を段階的に追加する。ユーザーデータ永続化を基盤として、スキルXP・成長グラフ、シナリオアンロック、デイリー/ウィークリークエスト、観戦モードクイズ、バッジシステムを順に実装する。実装言語はPython、テストはpytest + hypothesisを使用する。

## タスク

- [ ] 1. UserDataService（ユーザーデータ永続化）の実装
  - [ ] 1.1 `services/user_data_service.py` を作成し、UserDataServiceクラスを実装する
    - `user_data/` ディレクトリの自動作成
    - `_get_file_path`: user_idからJSONファイルパスを生成
    - `_create_default_data`: デフォルトユーザーデータ（skill_xp, badges, quests, unlock_status, stats等）を生成
    - `get_user_data`: JSONファイル読み込み。存在しない/破損時はデフォルト値を返す。破損時は `.bak` にリネーム
    - `save_user_data`: JSONファイルへの書き込み
    - _要件: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]* 1.2 Property 1 のプロパティベーステストを作成する
    - **Property 1: ユーザーデータ保存・読み込みラウンドトリップ**
    - hypothesisで有効なユーザーデータを生成し、save→getで等価性を検証
    - **検証対象: 要件 1.2, 1.3, 1.5**

  - [ ]* 1.3 UserDataServiceのユニットテストを作成する
    - `tests/test_services/test_user_data_service.py` を作成
    - 正常系: 新規ユーザーデータ作成、保存・読み込み
    - 異常系: 破損JSONファイル、存在しないファイル、ディレクトリ未存在
    - エッジケース: 空データ、大量履歴データ
    - _要件: 1.1, 1.2, 1.3, 1.4_

- [ ] 2. チェックポイント - UserDataService動作確認
  - すべてのテストが通ることを確認し、不明点があればユーザーに質問する。

- [ ] 3. GamificationService（スキルXP・成長グラフ）の実装
  - [ ] 3.1 `services/gamification_service.py` を作成し、GamificationServiceクラスを実装する
    - `calculate_xp_from_scores`: 6軸スコア（0-100）からXPを計算。スコア範囲外は0-100にクランプ、不足キーは0扱い
    - `add_xp`: XPを加算しユーザーデータを更新。xp_historyに履歴追加
    - `get_growth_data`: 成長グラフ用データ（個人ベスト、週次比較、直近10回平均）を返す
    - `get_skill_summary`: 現在のスキルXPサマリーを返す
    - ハラスメントシナリオではゲーム的言語を使用しない処理
    - _要件: 2.1, 2.2, 2.3, 2.4, 2.5_


  - [ ]* 3.2 Property 2 のプロパティベーステストを作成する
    - **Property 2: 6軸スコアからのXP計算の正当性**
    - hypothesisで6軸スコア辞書（各軸0-100）を生成し、XP値が非負整数かつスコアに比例することを検証
    - **検証対象: 要件 2.1, 2.2**

  - [ ]* 3.3 Property 3 のプロパティベーステストを作成する
    - **Property 3: 成長データの自己比較計算**
    - hypothesisでXP履歴リスト（1件以上）を生成し、個人ベスト・週次比較・直近10回平均の3指標を検証
    - **検証対象: 要件 2.4**

  - [ ]* 3.4 GamificationServiceのユニットテストを作成する
    - `tests/test_services/test_gamification_service.py` を作成
    - 正常系: XP計算、XP加算、成長データ取得
    - 異常系: スコア範囲外（負値、100超）、スコアキー不足
    - エッジケース: 履歴0件、履歴10件超、ハラスメントシナリオ
    - _要件: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 4. UnlockService（シナリオアンロック）の実装
  - [ ] 4.1 `services/unlock_service.py` を作成し、UnlockServiceクラスを実装する
    - `UNLOCK_THRESHOLDS`: beginner→intermediate（3完了）、intermediate→advanced（3完了）
    - `get_unlock_status`: 全シナリオのアンロック状態を返す
    - `check_and_unlock`: 完了数に基づき新規アンロックを判定
    - `is_scenario_unlocked`: 指定シナリオのアンロック判定
    - `get_unlock_progress`: 各レベルのアンロック進捗（現在値/必要値）を返す
    - 新規ユーザーはbeginnerのみアンロック
    - _要件: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ]* 4.2 Property 4 のプロパティベーステストを作成する
    - **Property 4: シナリオアンロック判定**
    - hypothesisで難易度レベルと完了数を生成し、閾値以上でのみアンロックされることを検証
    - **検証対象: 要件 3.2, 3.3**

  - [ ]* 4.3 Property 5 のプロパティベーステストを作成する
    - **Property 5: シナリオ一覧データの完全性**
    - hypothesisでアンロック状態を生成し、各エントリに難易度・アンロック状態・条件が含まれることを検証
    - **検証対象: 要件 3.4, 3.5**

  - [ ]* 4.4 UnlockServiceのユニットテストを作成する
    - `tests/test_services/test_unlock_service.py` を作成
    - 正常系: 初期状態（beginnerのみ）、段階的アンロック
    - エッジケース: 閾値ちょうど、閾値-1、全レベルアンロック済み
    - _要件: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 5. チェックポイント - XP・アンロック動作確認
  - すべてのテストが通ることを確認し、不明点があればユーザーに質問する。

- [ ] 6. QuestService（デイリー/ウィークリークエスト）の実装
  - [ ] 6.1 `services/quest_service.py` を作成し、QuestServiceクラスを実装する
    - `DAILY_QUEST_TEMPLATES` / `WEEKLY_QUEST_TEMPLATES` の定義
    - `generate_daily_quests`: デイリークエスト生成（期限: 当日終了）
    - `generate_weekly_quests`: ウィークリークエスト生成（期限: 週末）
    - `get_active_quests`: 有効なクエスト一覧を返す。期限切れは自動更新
    - `check_quest_completion`: アクティビティに基づきクエスト完了を判定、ボーナスXP付与
    - `_is_quest_expired`: 期限切れ判定
    - _要件: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 6.2 Property 6 のプロパティベーステストを作成する
    - **Property 6: クエスト生成の有効性**
    - hypothesisでユーザーIDと日付を生成し、クエストの必須フィールドと値の妥当性を検証
    - **検証対象: 要件 4.1, 4.2**

  - [ ]* 6.3 Property 7 のプロパティベーステストを作成する
    - **Property 7: クエスト完了判定とXP付与**
    - hypothesisでtarget_valueと現在値を生成し、C≥Tの場合のみ完了・XP付与されることを検証
    - **検証対象: 要件 4.3, 4.4**

  - [ ]* 6.4 Property 8 のプロパティベーステストを作成する
    - **Property 8: 期限切れクエストの置き換え**
    - hypothesisで期限切れクエストリストを生成し、get_active_questsの結果に期限切れが含まれないことを検証
    - **検証対象: 要件 4.5**

  - [ ]* 6.5 QuestServiceのユニットテストを作成する
    - `tests/test_services/test_quest_service.py` を作成
    - 正常系: クエスト生成、完了判定、XP付与
    - 異常系: テンプレート不足時のフォールバック
    - エッジケース: 期限切れクエスト、日付境界、target_value=0
    - _要件: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 7. QuizService（観戦モードクイズ）の実装
  - [ ] 7.1 `services/quiz_service.py` を作成し、QuizServiceクラスを実装する
    - `QUIZ_INTERVAL = 5`: 会話数ごとのクイズ生成間隔
    - `should_generate_quiz`: message_countがQUIZ_INTERVALの正の倍数かを判定
    - `generate_quiz`: LLMを使用してコンテキストベースのクイズ（3-4択）を生成。LLM障害時はフォールバッククイズを使用
    - `evaluate_answer`: 回答評価とLLMによる解説生成。正解時はボーナスXP情報を含む
    - `get_session_summary`: セッション終了時のクイズ正答率サマリー
    - _要件: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 7.2 Property 9 のプロパティベーステストを作成する
    - **Property 9: クイズ生成タイミング判定**
    - hypothesisで非負整数を生成し、QUIZ_INTERVALの正の倍数の場合のみTrueを返すことを検証
    - **検証対象: 要件 5.1**

  - [ ]* 7.3 Property 10 のプロパティベーステストを作成する
    - **Property 10: クイズ選択肢数の不変条件**
    - hypothesisでクイズデータを生成し、choices数が3-4、correct_answerが有効インデックスであることを検証
    - **検証対象: 要件 5.2**

  - [ ]* 7.4 Property 11 のプロパティベーステストを作成する
    - **Property 11: クイズ正解時のXP付与**
    - hypothesisでクイズと回答を生成し、正解時のみ正のXP、不正解時は0であることを検証
    - **検証対象: 要件 5.4**

  - [ ]* 7.5 Property 12 のプロパティベーステストを作成する
    - **Property 12: クイズ正答率計算**
    - hypothesisでクイズ回答履歴リスト（1件以上）を生成し、正答率が正しく計算されることを検証
    - **検証対象: 要件 5.5**

  - [ ]* 7.6 QuizServiceのユニットテストを作成する
    - `tests/test_services/test_quiz_service.py` を作成
    - 正常系: クイズ生成、回答評価、正答率計算
    - 異常系: LLM API呼び出し失敗、レスポンスパース失敗、選択肢数範囲外
    - エッジケース: message_count=0、フォールバッククイズ使用
    - _要件: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 8. チェックポイント - クエスト・クイズ動作確認
  - すべてのテストが通ることを確認し、不明点があればユーザーに質問する。

- [ ] 9. BadgeService（バッジシステム）の実装
  - [ ] 9.1 `services/badge_service.py` を作成し、BadgeServiceクラスを実装する
    - バッジ定義（継続性: first_step, three_day_streak, seven_day_streak / 多様性: explorer, all_rounder, quiz_challenger / 改善度: growth_spurt, personal_best, balanced_growth）
    - `check_badge_eligibility`: ユーザー統計データに基づきバッジ獲得条件をチェック
    - `get_all_badges`: 全バッジ一覧（獲得済み/未獲得+条件+進捗）を返す
    - `award_badge`: バッジ付与と通知データ生成
    - `get_badge_progress`: 特定バッジの達成進捗を返す
    - _要件: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 9.2 Property 13 のプロパティベーステストを作成する
    - **Property 13: バッジ獲得条件判定**
    - hypothesisでユーザー統計データを生成し、条件を満たす場合のみバッジが付与されることを検証
    - **検証対象: 要件 6.1**

  - [ ]* 9.3 Property 14 のプロパティベーステストを作成する
    - **Property 14: バッジ一覧の完全性**
    - hypothesisでユーザーデータを生成し、全定義バッジが含まれ、未獲得バッジに条件・進捗が含まれることを検証
    - **検証対象: 要件 6.3, 6.5**

  - [ ]* 9.4 BadgeServiceのユニットテストを作成する
    - `tests/test_services/test_badge_service.py` を作成
    - 正常系: バッジ獲得判定、バッジ付与、通知データ生成
    - エッジケース: 全バッジ獲得済み、条件ちょうど達成、バッジカテゴリ3種類の確認
    - _要件: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 10. APIルートとサービス統合
  - [ ] 10.1 `routes/gamification_routes.py` を作成し、ゲーミフィケーション関連のBlueprintを実装する
    - `GET /api/gamification/dashboard`: ダッシュボード（XP、クエスト、バッジ概要）
    - `GET /api/gamification/growth`: 成長グラフデータ
    - `GET /api/gamification/quests`: アクティブクエスト一覧
    - `GET /api/gamification/badges`: バッジ一覧
    - `GET /api/gamification/unlock-status`: シナリオアンロック状態
    - _要件: 2.3, 3.5, 4.4, 6.3_

  - [ ] 10.2 `routes/quiz_routes.py` を作成し、観戦クイズ関連のBlueprintを実装する
    - `POST /api/quiz/generate`: クイズ生成
    - `POST /api/quiz/answer`: クイズ回答・評価
    - `GET /api/quiz/summary`: セッションサマリー
    - _要件: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ] 10.3 既存の `app.py` にBlueprintを登録し、セッション完了時のXP計算・クエスト進捗更新・バッジチェック・アンロック判定のフックを統合する
    - SessionService完了時にGamificationService.add_xpを呼び出す
    - XP加算後にQuestService.check_quest_completionを呼び出す
    - アクティビティ後にBadgeService.check_badge_eligibilityを呼び出す
    - シナリオ完了後にUnlockService.check_and_unlockを呼び出す
    - _要件: 2.1, 3.2, 3.3, 4.3, 6.1_

  - [ ]* 10.4 APIルートの統合テストを作成する
    - 各エンドポイントのレスポンス形式を検証
    - セッション完了→XP加算→クエスト進捗→バッジチェック→アンロック判定の一連フローを検証
    - _要件: 2.1, 3.2, 4.3, 6.1_

- [ ] 11. 最終チェックポイント - 全テスト実行
  - すべてのテストが通ることを確認し、不明点があればユーザーに質問する。
  - `pytest tests/test_services/ -k "gamification or user_data or unlock or quest or quiz or badge" --cov=services --cov-report=term-missing -v`

## 備考

- `*` マーク付きのタスクはオプションであり、MVP実装時にはスキップ可能
- 各タスクは具体的な要件番号を参照しており、トレーサビリティを確保
- チェックポイントで段階的に動作を検証
- プロパティベーステストは普遍的な正当性を検証し、ユニットテストは具体例・エッジケースを検証する
