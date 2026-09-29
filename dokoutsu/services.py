from datetime import timedelta

from django.utils import timezone

from .models import EmailSendLog

# メール送信回数の制限(基本設計書「3.2 メール送信回数の制限」)
EMAIL_SEND_LIMIT = 5
EMAIL_SEND_WINDOW = timedelta(hours=24)
EMAIL_SEND_LIMIT_MESSAGE = "送信回数の上限に達しました。時間をおいてもう一度お試しください"


def reserve_email_send(email, purpose):
    """直近24時間の送信回数が上限未満なら、今回の送信を記録してTrueを返す。上限に達していればFalseを返す。

    大文字・小文字を変えただけの同じメールアドレスで上限をすり抜けられないよう、小文字にそろえて数える。
    """
    address = email.lower()
    logs = EmailSendLog.objects.filter(email=address, purpose=purpose)
    logs.filter(created_at__lte=timezone.now() - EMAIL_SEND_WINDOW).delete()
    if logs.count() >= EMAIL_SEND_LIMIT:
        return False
    EmailSendLog.objects.create(email=address, purpose=purpose)
    return True
