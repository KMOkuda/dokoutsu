import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 動作確認用の暫定値。本実装時はセキュリティ方針(2.5 秘密情報の管理)に従い、
# 環境変数からの読み込みを必須にする。
SECRET_KEY = os.environ.get("SECRET_KEY", "test-only-not-for-production")
DEBUG = os.environ.get("DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }
}

STATIC_URL = "static/"
