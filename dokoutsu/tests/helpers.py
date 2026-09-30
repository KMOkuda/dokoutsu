"""テストで共通に使う補助関数"""

import re
from urllib.parse import urlparse

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def uid_token(user):
    """パスワード再発行リンクに使う、ユーザーIDを変換した値とトークンを返す。"""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uidb64, token


def activation_path_from_mail():
    """直近に送った登録確認メールの本文から、確認リンクのパス部分を取り出す。"""
    url = re.search(r"https?://\S+", mail.outbox[-1].body).group(0)
    return urlparse(url).path
