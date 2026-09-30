"""画面ごとのビュー。画面コード(基本設計書「2.1 画面一覧」)ごとにファイルを分けている。

urls.pyからは views.signup_view のように参照するため、ここでまとめて読み込む。
"""

from .answers import answer_create_view, answer_list_view
from .login import login_view, logout_view
from .password_reset import password_reset_confirm_view, password_reset_view
from .problems import (
    active_problems_view,
    archive_problems_view,
    problem_close_view,
    problem_created_view,
    problem_delete_view,
    problem_new_view,
)
from .signup import activate_view, signup_sent_view, signup_view

__all__ = [
    "activate_view",
    "active_problems_view",
    "answer_create_view",
    "answer_list_view",
    "archive_problems_view",
    "login_view",
    "logout_view",
    "password_reset_confirm_view",
    "password_reset_view",
    "problem_close_view",
    "problem_created_view",
    "problem_delete_view",
    "problem_new_view",
    "signup_sent_view",
    "signup_view",
]
