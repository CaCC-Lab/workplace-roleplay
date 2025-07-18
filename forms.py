"""
フォーム定義

ユーザー認証に関するフォームクラス
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User


class LoginForm(FlaskForm):
    """ログインフォーム"""
    username_or_email = StringField('ユーザー名またはメールアドレス', validators=[DataRequired()])
    password = PasswordField('パスワード', validators=[DataRequired()])
    remember_me = BooleanField('ログイン状態を保持する')
    submit = SubmitField('ログイン')


class RegistrationForm(FlaskForm):
    """ユーザー登録フォーム"""
    username = StringField('ユーザー名', validators=[
        DataRequired(),
        Length(min=3, max=20, message='ユーザー名は3文字以上20文字以下で入力してください'),
    ])
    email = StringField('メールアドレス', validators=[
        DataRequired(),
        Email(message='有効なメールアドレスを入力してください')
    ])
    password = PasswordField('パスワード', validators=[
        DataRequired(),
        Length(min=8, message='パスワードは8文字以上で入力してください')
    ])
    password2 = PasswordField('パスワード（確認）', validators=[
        DataRequired(),
        EqualTo('password', message='パスワードが一致しません')
    ])
    submit = SubmitField('登録')
    
    def validate_username(self, username):
        """ユーザー名の重複チェック"""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('このユーザー名は既に使用されています')
    
    def validate_email(self, email):
        """メールアドレスの重複チェック"""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('このメールアドレスは既に使用されています')