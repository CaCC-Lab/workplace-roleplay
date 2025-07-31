"""認証ブループリント（ダミー実装）"""
from flask import Blueprint, redirect, url_for

# 認証ブループリントの作成
auth = Blueprint("auth", __name__, url_prefix="/auth")


@auth.route("/login")
def login():
    """ログインページ（ダミー）"""
    # 認証機能が実装されるまでホームにリダイレクト
    return redirect(url_for("index"))


@auth.route("/logout")
def logout():
    """ログアウト（ダミー）"""
    return redirect(url_for("index"))


@auth.route("/register")
def register():
    """登録ページ（ダミー）"""
    return redirect(url_for("index"))