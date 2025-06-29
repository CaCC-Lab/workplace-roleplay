"""
CSP（Content Security Policy）使用例
"""

from flask import Flask, render_template_string, jsonify
from utils.csp_middleware import init_csp, CSPNonce
from utils.security import SecurityUtils

# Flaskアプリケーションの初期化
app = Flask(__name__)
app.config['SECRET_KEY'] = 'demo-secret-key'

# CSPミドルウェアの初期化（Phase 1: Report-Onlyモード）
csp = init_csp(app, phase=CSPNonce.PHASE_REPORT_ONLY)


@app.route('/')
def index():
    """セキュアなHTMLページの例"""
    # テンプレート内でcsp_nonce()関数を使用
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>CSP Demo</title>
    <meta charset="utf-8">
    <!-- nonceを使用したインラインスタイル -->
    <style nonce="{{ csp_nonce() }}">
        body { font-family: Arial, sans-serif; margin: 20px; }
        .safe { color: green; }
        .demo { background: #f0f0f0; padding: 10px; }
    </style>
</head>
<body>
    <h1>CSP Demo Page</h1>
    
    <div class="demo">
        <h2>Safe Content</h2>
        <p class="safe">このコンテンツはCSPで保護されています。</p>
        
        <!-- nonceを使用したインラインスクリプト -->
        <script nonce="{{ csp_nonce() }}">
            console.log('Safe inline script with nonce');
            
            // DOM操作の例
            document.addEventListener('DOMContentLoaded', function() {
                const button = document.getElementById('safeButton');
                button.addEventListener('click', function() {
                    alert('Safe button clicked!');
                });
            });
        </script>
        
        <button id="safeButton">Safe Button</button>
    </div>
    
    <div class="demo">
        <h2>API Call Example</h2>
        <button onclick="makeApiCall()">Make API Call</button>
        <div id="apiResult"></div>
        
        <script nonce="{{ csp_nonce() }}">
            async function makeApiCall() {
                try {
                    const response = await fetch('/api/data');
                    const data = await response.json();
                    document.getElementById('apiResult').innerHTML = 
                        '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    console.error('API call failed:', error);
                }
            }
        </script>
    </div>
    
    <div class="demo">
        <h2>CSP Status</h2>
        <p>現在のCSPフェーズ: {{ phase }}</p>
        <a href="/admin/csp-violations">CSP違反レポートを見る</a>
    </div>
</body>
</html>
    ''', phase=app.config.get('CSP_PHASE', 1))


@app.route('/unsafe')
def unsafe_page():
    """CSP違反を含むページの例（テスト用）"""
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Unsafe Page</title>
</head>
<body>
    <h1>Unsafe Page (CSP Violations)</h1>
    
    <!-- CSP違反：nonceなしのインラインスクリプト -->
    <script>
        console.log('This script will be blocked by CSP');
        eval('console.log("eval is dangerous")');  // さらに危険
    </script>
    
    <!-- CSP違反：インラインイベントハンドラー -->
    <button onclick="alert('This will be blocked')">Unsafe Button</button>
    
    <!-- CSP違反：外部ドメインからのスクリプト -->
    <script src="https://malicious.example.com/evil.js"></script>
    
    <p>このページはCSP違反を含んでいます。ブラウザのコンソールで違反を確認してください。</p>
</body>
</html>
    ''')


@app.route('/api/data')
def api_data():
    """API エンドポイントの例"""
    # セキュアなJSONレスポンス
    data = {
        'message': 'Hello from API',
        'timestamp': '2024-01-01T00:00:00Z',
        'user_input': SecurityUtils.sanitize_input('Sample <script>alert("xss")</script> input')
    }
    return jsonify(data)


@app.route('/admin/csp-violations')
def csp_violations():
    """CSP違反レポートページ"""
    # 違反サマリーを取得
    summary = csp.get_violation_summary()
    
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>CSP Violations Report</title>
    <style nonce="{{ csp_nonce() }}">
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .high { color: red; }
        .medium { color: orange; }
        .low { color: green; }
    </style>
</head>
<body>
    <h1>CSP Violations Report</h1>
    
    <div>
        <h2>Summary</h2>
        <p>Total violations: {{ summary.total_violations }}</p>
    </div>
    
    {% if summary.violations_by_directive %}
    <div>
        <h2>Violations by Directive</h2>
        <table>
            <tr>
                <th>Directive</th>
                <th>Count</th>
            </tr>
            {% for directive, count in summary.violations_by_directive.items() %}
            <tr>
                <td>{{ directive }}</td>
                <td>{{ count }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
    {% endif %}
    
    {% if summary.common_blocked_uris %}
    <div>
        <h2>Most Blocked URIs</h2>
        <table>
            <tr>
                <th>URI</th>
                <th>Count</th>
            </tr>
            {% for uri, count in summary.common_blocked_uris %}
            <tr>
                <td>{{ uri }}</td>
                <td>{{ count }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
    {% endif %}
    
    {% if summary.recent_violations %}
    <div>
        <h2>Recent Violations</h2>
        <table>
            <tr>
                <th>Timestamp</th>
                <th>Directive</th>
                <th>Blocked URI</th>
                <th>Document</th>
            </tr>
            {% for violation in summary.recent_violations %}
            <tr>
                <td>{{ violation.timestamp }}</td>
                <td>{{ violation.violated_directive }}</td>
                <td>{{ violation.blocked_uri }}</td>
                <td>{{ violation.document_uri }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
    {% endif %}
    
    <div>
        <h2>Actions</h2>
        <button onclick="clearViolations()">Clear Violations</button>
        <button onclick="location.reload()">Refresh</button>
        
        <script nonce="{{ csp_nonce() }}">
            async function clearViolations() {
                if (confirm('Clear all violation records?')) {
                    try {
                        const response = await fetch('/admin/clear-violations', {
                            method: 'POST'
                        });
                        if (response.ok) {
                            location.reload();
                        }
                    } catch (error) {
                        alert('Failed to clear violations');
                    }
                }
            }
        </script>
    </div>
    
    <p><a href="/">Back to main page</a></p>
</body>
</html>
    ''', summary=summary)


@app.route('/admin/clear-violations', methods=['POST'])
def clear_violations():
    """CSP違反ログをクリア"""
    csp.clear_violations()
    return jsonify({'status': 'cleared'})


@app.route('/admin/csp-config')
def csp_config():
    """CSP設定ページ"""
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>CSP Configuration</title>
    <style nonce="{{ csp_nonce() }}">
        .config-section { margin: 20px 0; padding: 15px; border: 1px solid #ccc; }
        .phase { font-weight: bold; color: blue; }
        .warning { color: red; }
    </style>
</head>
<body>
    <h1>CSP Configuration</h1>
    
    <div class="config-section">
        <h2>Current Configuration</h2>
        <p>Phase: <span class="phase">{{ current_phase }}</span></p>
        <p>Report Only: {{ report_only }}</p>
        <p>Report URI: {{ report_uri }}</p>
    </div>
    
    <div class="config-section">
        <h2>Phase Information</h2>
        <h3>Phase 1: Report-Only</h3>
        <ul>
            <li>Monitors violations without blocking</li>
            <li>Allows 'unsafe-inline' and 'unsafe-eval'</li>
            <li>Recommended for initial deployment</li>
        </ul>
        
        <h3>Phase 2: Mixed</h3>
        <ul>
            <li>Removes 'unsafe-eval'</li>
            <li>Keeps 'unsafe-inline' for styles</li>
            <li>Adds upgrade-insecure-requests</li>
        </ul>
        
        <h3>Phase 3: Strict</h3>
        <ul>
            <li>Removes all 'unsafe-*' directives</li>
            <li>Requires nonce for all inline content</li>
            <li>Maximum security</li>
        </ul>
    </div>
    
    <div class="config-section">
        <h2>Migration Checklist</h2>
        <ul>
            <li>✓ CSP implementation completed</li>
            <li>✓ Violation monitoring active</li>
            <li>⚠ Review violations before phase upgrade</li>
            <li>⚠ Test all functionality after phase change</li>
        </ul>
    </div>
    
    <p class="warning">
        Note: Phase changes should be done carefully after analyzing violation reports.
    </p>
    
    <p><a href="/">Back to main page</a></p>
</body>
</html>
    ''', 
    current_phase=app.config.get('CSP_PHASE', 1),
    report_only=app.config.get('CSP_REPORT_ONLY', True),
    report_uri=app.config.get('CSP_REPORT_URI', '/api/csp-report')
    )


if __name__ == '__main__':
    print("CSP Demo Application Starting...")
    print("Visit http://localhost:5000/ for the main page")
    print("Visit http://localhost:5000/unsafe for CSP violation examples")
    print("Visit http://localhost:5000/admin/csp-violations for violation reports")
    print("Visit http://localhost:5000/admin/csp-config for configuration info")
    
    app.run(debug=True, port=5000)