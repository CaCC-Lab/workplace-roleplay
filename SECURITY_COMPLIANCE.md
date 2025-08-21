# Google Gemini API 規約遵守ガイドライン

## 🚨 緊急修正完了 - 規約違反リスクの解消

### 修正概要
2025-08-21: Google Gemini API利用規約に違反する可能性のある実装を発見し、緊急修正を実施しました。

## 1. 発見された規約違反リスク

### ⚠️ 旧実装の問題 (`api_key_manager.py`)
```python
# 明確な規約違反意図の表明
"""複数のAPIキーを管理し、レート制限を回避するためのローテーションを行う"""
```

**問題点:**
1. **レート制限回避の明示的意図** - Google APIの正当な保護機能の迂回
2. **複数APIキーローテーション** - Fair Use Policyへの違反可能性
3. **エラー時の別キー切り替え** - サービス妨害行為に該当するリスク

### 🔴 Google Cloud Platform 利用規約への抵触リスク
- **禁止事項**: サービスの通常運用への妨害行為
- **該当箇所**: レート制限は正当なサービス保護メカニズム
- **リスク**: アカウント停止、法的責任、サービス継続不能

## 2. 規約準拠実装への移行

### ✅ 新実装 (`compliant_api_manager.py`)

#### 主要改善点
1. **単一APIキー使用** - 規約に準拠した正当な利用
2. **保守的レート制限** - 公式制限より低い設定で安全性確保
3. **Exponential Backoff** - Google推奨のエラー処理実装
4. **透明性のある制限遵守** - ユーザーに待機時間を明示

#### コード例
```python
# 規約準拠のAPI使用パターン
manager = CompliantAPIManager()
api_key = manager.get_api_key()  # レート制限を厳格チェック
# API呼び出し
manager.record_success()  # 成功を記録

# エラー時
manager.record_error(error)  # 適切なバックオフ処理
```

## 3. アプリケーションでの使用方法

### 修正済み関数の使用
```python
# 旧版（規約違反リスク）
# from api_key_manager import get_google_api_key

# 新版（規約準拠）
from compliant_api_manager import get_compliant_google_api_key

try:
    api_key = get_compliant_google_api_key()
    # API使用
    record_compliant_api_usage()
except RateLimitException as e:
    print(f"規約遵守のため待機が必要: {e}")
except Exception as e:
    handle_compliant_api_error(e)
```

## 4. 規約遵守のベストプラクティス

### ✅ 推奨事項
1. **単一APIキーの使用** - 複数アカウント・キーの使い回し禁止
2. **公式制限の遵守** - 保守的な制限設定で安全性確保
3. **適切なエラーハンドリング** - Exponential Backoffの実装
4. **透明性の確保** - ユーザーへの明確な状況説明

### ❌ 禁止事項
1. **レート制限回避の意図的実装**
2. **複数APIキーのローテーション使用**
3. **制限エラー時の即座な別キー切り替え**
4. **Googleサービスの正常運用を妨害する行為**

## 5. モニタリングと継続的コンプライアンス

### 使用状況の監視
```python
# API使用状況の確認
status = manager.get_status()
print(f"今分のリクエスト数: {status['requests_last_minute']}")
print(f"今時間のリクエスト数: {status['requests_last_hour']}")
print(f"規約準拠実装: {status['compliant_implementation']}")
```

### 定期的な規約確認
- Google Cloud Platform Terms of Service の確認
- Gemini API Acceptable Use Policy の更新チェック
- 実装の継続的なコンプライアンス確認

## 6. 緊急時の対応手順

### アカウント制限時の対応
1. **即座のアクセス停止** - 追加的な違反行為の回避
2. **Googleサポートへの連絡** - 状況の説明と改善策の提示
3. **規約準拠実装の証明** - 修正済みコードの提示
4. **代替サービスの準備** - サービス継続のためのバックアッププラン

### 継続的改善
- 規約変更の定期確認
- 実装の継続的監査
- セキュリティチーム/法務チームとの連携

---

## 📞 問い合わせ

規約遵守に関する質問や懸念がある場合は、開発チームまでお問い合わせください。

**重要**: このドキュメントは法的助言ではありません。正式な法的判断が必要な場合は、適切な法的専門家にご相談ください。