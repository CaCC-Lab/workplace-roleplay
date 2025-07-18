#!/usr/bin/env python3
"""
認証システムのテスト用アプリケーション
最小限の機能で認証システムをテスト
"""
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-for-testing')
app.config['WTF_CSRF_ENABLED'] = True

# Flask-Login と Bcrypt の初期化
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'このページにアクセスするにはログインが必要です。'

bcrypt = Bcrypt(app)

# 仮のユーザーデータ（データベース接続の代わり）
USERS = {
    'testuser1': {
        'id': 1,
        'username': 'testuser1',
        'email': 'test1@example.com',
        'password_hash': None,  # 起動時に設定
        'is_active': True
    },
    'testuser2': {
        'id': 2,
        'username': 'testuser2',
        'email': 'test2@example.com',
        'password_hash': None,  # 起動時に設定
        'is_active': True
    }
}

# テストユーザーのパスワードハッシュを設定
for user in USERS.values():
    if user['username'] == 'testuser1':
        user['password_hash'] = bcrypt.generate_password_hash('testpass123').decode('utf-8')
    elif user['username'] == 'testuser2':
        user['password_hash'] = bcrypt.generate_password_hash('testpass456').decode('utf-8')

# User クラス（Flask-Login用）
class User:
    def __init__(self, user_dict):
        self.id = user_dict['id']
        self.username = user_dict['username']
        self.email = user_dict['email']
        self.password_hash = user_dict['password_hash']
        self.is_active = user_dict['is_active']
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)

# ログインフォーム
class LoginForm(FlaskForm):
    username_or_email = StringField('ユーザー名またはメールアドレス', validators=[DataRequired()])
    password = PasswordField('パスワード', validators=[DataRequired()])
    remember_me = BooleanField('ログイン状態を保持する')
    submit = SubmitField('ログイン')

# Flask-Login のユーザーローダー
@login_manager.user_loader
def load_user(user_id):
    for user_data in USERS.values():
        if str(user_data['id']) == user_id:
            return User(user_data)
    return None

# ルート
@app.route('/')
def index():
    return render_template('index_test.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        username_or_email = form.username_or_email.data
        password = form.password.data
        
        # ユーザーを検索
        user_data = None
        for data in USERS.values():
            if data['username'] == username_or_email or data['email'] == username_or_email:
                user_data = data
                break
        
        if user_data:
            user = User(user_data)
            if user.check_password(password):
                login_user(user, remember=form.remember_me.data)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                form.password.errors.append('パスワードが正しくありません')
        else:
            form.username_or_email.errors.append('ユーザーが見つかりません')
    
    return render_template('auth/login_test.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/protected')
@login_required
def protected():
    return f'<h1>保護されたページ</h1><p>ようこそ、{current_user.username}さん！</p><a href="{url_for("logout")}">ログアウト</a>'

# 404エラーハンドラー
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

if __name__ == '__main__':
    print("認証システムテストサーバーを起動中...")
    print("テストユーザー:")
    print("  - ユーザー名: testuser1, パスワード: testpass123")
    print("  - ユーザー名: testuser2, パスワード: testpass456")
    print("")
    app.run(debug=True, port=5001)