"""
認証モジュール

ユーザー認証に関するビューとロジック
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from models import db, User
from forms import LoginForm, RegistrationForm
from services import UserService
from utils.security import CSRFToken
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """ログイン画面"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # ユーザー名またはメールアドレスでユーザーを検索
        user = User.query.filter(
            (User.username == form.username_or_email.data) | 
            (User.email == form.username_or_email.data)
        ).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('ユーザー名/メールアドレスまたはパスワードが正しくありません', 'danger')
            logger.warning(f"ログイン失敗: {form.username_or_email.data}")
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('このアカウントは無効化されています', 'warning')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        logger.info(f"ユーザーログイン成功: {user.username}")
        
        # リダイレクト先の処理
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        
        flash(f'ようこそ、{user.username}さん！', 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html', title='ログイン', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """ユーザー登録画面"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # 新しいユーザーを作成
            user = User(
                username=form.username.data,
                email=form.email.data
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"新規ユーザー登録: {user.username}")
            flash('登録が完了しました！ログインしてください。', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"ユーザー登録エラー: {e}")
            flash('登録に失敗しました。しばらく時間をおいてから再度お試しください。', 'danger')
    
    return render_template('auth/register.html', title='ユーザー登録', form=form)


@auth_bp.route('/logout', methods=['POST'])
@login_required
@CSRFToken.require_csrf
def logout():
    """ログアウト"""
    username = current_user.username
    logout_user()
    logger.info(f"ユーザーログアウト: {username}")
    flash('ログアウトしました', 'info')
    return redirect(url_for('index'))