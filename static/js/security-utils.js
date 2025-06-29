/**
 * セキュリティ関連のユーティリティ関数
 * XSS対策のためのクライアントサイドエスケープ処理
 */

class SecurityUtils {
    /**
     * HTMLエスケープを行う
     * @param {string} str - エスケープする文字列
     * @returns {string} エスケープされた文字列
     */
    static escapeHtml(str) {
        if (typeof str !== 'string') {
            return '';
        }
        
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
    
    /**
     * HTMLを安全に挿入する
     * @param {string} html - 挿入するHTML文字列
     * @returns {string} 安全なHTML文字列
     */
    static sanitizeHtml(html) {
        // 危険なタグやイベントハンドラを除去
        const tempDiv = document.createElement('div');
        tempDiv.textContent = html;
        return tempDiv.innerHTML;
    }
    
    /**
     * URLパラメータをエスケープする
     * @param {string} param - パラメータ値
     * @returns {string} エスケープされたパラメータ
     */
    static escapeUrlParam(param) {
        return encodeURIComponent(param);
    }
    
    /**
     * JSONデータを安全に挿入する
     * @param {object} data - JSONデータ
     * @returns {string} 安全なJSON文字列
     */
    static safeJsonStringify(data) {
        return JSON.stringify(data)
            .replace(/</g, '\\u003c')
            .replace(/>/g, '\\u003e')
            .replace(/&/g, '\\u0026');
    }
    
    /**
     * DOMベースのテキスト挿入（最も安全）
     * @param {HTMLElement} element - 挿入先の要素
     * @param {string} text - 挿入するテキスト
     */
    static setTextContent(element, text) {
        if (element && typeof text === 'string') {
            element.textContent = text;
        }
    }
    
    /**
     * メッセージ表示用の安全なHTML生成
     * @param {string} content - メッセージ内容
     * @param {string} className - CSSクラス名
     * @returns {HTMLElement} 安全なメッセージ要素
     */
    static createSafeMessageElement(content, className) {
        const messageDiv = document.createElement('div');
        messageDiv.className = className;
        
        // テキストコンテンツとして設定（XSS対策）
        messageDiv.textContent = content;
        
        return messageDiv;
    }
    
    /**
     * 入力値の検証
     * @param {string} input - 検証する入力値
     * @returns {boolean} 有効な場合true
     */
    static validateInput(input) {
        // Null文字やその他の危険な文字を検出
        if (input.includes('\x00')) {
            return false;
        }
        
        // スクリプトタグの検出
        const scriptPattern = /<script[^>]*>.*?<\/script>/gi;
        if (scriptPattern.test(input)) {
            return false;
        }
        
        // イベントハンドラの検出
        const eventPattern = /on\w+\s*=/gi;
        if (eventPattern.test(input)) {
            return false;
        }
        
        return true;
    }
}