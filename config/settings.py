import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Railway上ではRailwayが自動で設定するこの変数の有無で本番と判定する
IS_RAILWAY = "RAILWAY_ENVIRONMENT_NAME" in os.environ

# 本番では設定漏れで危険な状態のまま起動しないよう、DEBUGは既定でオフ、SECRET_KEYは必須にする
DEBUG = os.environ.get("DEBUG", "false" if IS_RAILWAY else "true").lower() == "true"
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if IS_RAILWAY:
        raise ImproperlyConfigured("環境変数 SECRET_KEY が設定されていません")
    # ローカル開発では起動のたびに使い捨ての鍵を作る(鍵の文字列をソースコードに書かないため)。
    # 再起動するとログイン状態は切れる
    SECRET_KEY = get_random_secret_key()
ALLOWED_HOSTS = ["*"]

# Railwayはhttpsを手前で終端してhttpで転送するため、転送元のプロトコルを信頼してhttps扱いにする
# (これがないとフォーム送信時のCSRF検証で送信元不一致の403になる)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
    CSRF_TRUSTED_ORIGINS = [f"https://{os.environ['RAILWAY_PUBLIC_DOMAIN']}"]
if IS_RAILWAY:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "dokoutsu",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{os.path.join(BASE_DIR, 'db.sqlite3')}"
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
]

LANGUAGE_CODE = "ja"
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
# 本番(gunicorn)ではDjangoが静的ファイルを配信しないため、WhiteNoiseで配信する
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# パスワード再発行リンクの有効期限(秒)。詳細設計書 6a では60分
PASSWORD_RESET_TIMEOUT = 60 * 60

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "active_problems"

# セキュリティ方針「2.2 セッションの保持期間」(.claude/skills/security-guideline/SKILL.md)
SESSION_COOKIE_AGE = 60 * 60 * 24 * 120  # 120日(約4ヶ月)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# セキュリティ方針「2.6 URL漏洩時の拡散防止」
SECURE_REFERRER_POLICY = "same-origin"

# パスワード再発行メールの送信元。本番ではAmazon SES経由のSMTP設定を環境変数から読み込む。
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@example.com")
