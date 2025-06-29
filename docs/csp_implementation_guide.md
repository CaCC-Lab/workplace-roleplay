# CSP（Content Security Policy）実装ガイド

## 概要

このガイドでは、Flask アプリケーションに Content Security Policy (CSP) を段階的に導入する方法を説明します。

## 実装戦略

### Phase 1: Report-Only モード（現在の推奨）

最初は Report-Only モードで開始し、既存の機能を壊さずに違反を監視します。

```python
# app.py の例
from flask import Flask
from utils.csp_middleware import init_csp, CSPNonce

app = Flask(__name__)

# Phase 1: Report-Only モードで開始
csp = init_csp(app, phase=CSPNonce.PHASE_REPORT_ONLY)
```

### Phase 2: 部分的な強制

一部の危険な機能（eval など）を制限し始めます。

```python
# Phase 2 への移行
app.config['CSP_PHASE'] = CSPNonce.PHASE_MIXED
app.config['CSP_REPORT_ONLY'] = False  # 強制モードに変更
```

### Phase 3: 厳格なポリシー

完全なセキュリティを実現します。

```python
# Phase 3: 最も厳格なポリシー
app.config['CSP_PHASE'] = CSPNonce.PHASE_STRICT
```

## テンプレートの修正

### インラインスクリプトへの nonce 追加

```html
<!-- 修正前 -->
<script>
    console.log('Hello World');
</script>

<!-- 修正後 -->
<script nonce="{{ csp_nonce() }}">
    console.log('Hello World');
</script>
```

### インラインスタイルへの nonce 追加（Phase 3）

```html
<!-- 修正前 -->
<style>
    .custom { color: red; }
</style>

<!-- 修正後 -->
<style nonce="{{ csp_nonce() }}">
    .custom { color: red; }
</style>
```

## JavaScript の修正

### イベントハンドラーの外部化

```html
<!-- 修正前 -->
<button onclick="handleClick()">Click me</button>

<!-- 修正後 -->
<button id="myButton">Click me</button>
<script nonce="{{ csp_nonce() }}">
    document.getElementById('myButton').addEventListener('click', handleClick);
</script>
```

### eval の除去

```javascript
// 修正前
const func = eval('function() { return 42; }');

// 修正後
const func = function() { return 42; };
```

## 違反の監視と分析

### 違反レポートの確認

```python
# 違反サマリーを取得するエンドポイントの例
@app.route('/admin/csp-violations')
@login_required
def view_csp_violations():
    summary = csp.get_violation_summary()
    return render_template('admin/csp_violations.html', summary=summary)
```

### 違反の分析

```python
from utils.csp_middleware import CSPReportAnalyzer

# 違反を分析して改善提案を取得
analysis = CSPReportAnalyzer.analyze_violations(csp.violations)
for recommendation in analysis['recommendations']:
    print(f"Issue: {recommendation['issue']}")
    print(f"Priority: {recommendation['priority']}")
    print(f"Recommendation: {recommendation['recommendation']}")
```

## トラブルシューティング

### よくある違反と対処法

1. **インラインスクリプトの違反**
   - 原因: `<script>` タグ内の直接記述
   - 対処: nonce 属性を追加するか、外部ファイルに移動

2. **インラインスタイルの違反**
   - 原因: `style` 属性や `<style>` タグ
   - 対処: CSS クラスを使用するか、nonce を追加

3. **外部リソースのブロック**
   - 原因: CSP に含まれていない外部ドメイン
   - 対処: 信頼できるドメインを CSP に追加

4. **eval/Function の使用**
   - 原因: 動的なコード実行
   - 対処: より安全な代替手段に置き換え

### デバッグのヒント

1. **ブラウザのコンソールを確認**
   ```
   Refused to execute inline script because it violates the following Content Security Policy directive...
   ```

2. **CSP レポートを確認**
   ```python
   # 最近の違反を表示
   recent_violations = csp.violations[-10:]
   for v in recent_violations:
       print(f"{v['violated_directive']} - {v['blocked_uri']}")
   ```

3. **一時的に CSP を無効化**
   ```python
   from utils.csp_middleware import csp_exempt
   
   @app.route('/debug')
   @csp_exempt
   def debug_page():
       return render_template('debug.html')
   ```

## ベストプラクティス

1. **段階的な導入**
   - Phase 1 で最低 1 週間監視
   - 違反を分析してから次のフェーズへ

2. **チーム全体での取り組み**
   - 開発者全員が CSP を理解
   - コードレビューで CSP 違反をチェック

3. **継続的な監視**
   - 定期的に違反レポートを確認
   - 新しい外部リソースを追加する際は CSP を更新

4. **テストの自動化**
   - CSP ヘッダーの存在を確認するテスト
   - 重要な機能が CSP でブロックされないことを確認

## 設定例

### 開発環境

```python
# 開発環境では緩いポリシー
if app.debug:
    app.config['CSP_PHASE'] = CSPNonce.PHASE_REPORT_ONLY
```

### 本番環境

```python
# 本番環境では厳格なポリシー
if not app.debug:
    app.config['CSP_PHASE'] = CSPNonce.PHASE_STRICT
    app.config['CSP_REPORT_ONLY'] = False
```

## 次のステップ

1. まず Phase 1 (Report-Only) で CSP を有効化
2. 1-2 週間違反を監視
3. 違反を分析し、コードを修正
4. Phase 2 に移行し、徐々に制限を強化
5. 最終的に Phase 3 の厳格なポリシーを適用

CSP は強力なセキュリティ機能ですが、適切に実装しないとアプリケーションの機能を損なう可能性があります。段階的なアプローチで、安全かつ確実に導入しましょう。