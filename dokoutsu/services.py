from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import AnswerPostLog, EmailSendLog

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


# 回答投稿の頻度制限(基本設計書「3.3 回答投稿の頻度制限」)
ANSWER_POST_LIMIT = 10
ANSWER_POST_WINDOW = timedelta(minutes=10)
ANSWER_POST_LIMIT_MESSAGE = "短時間に多くの回答が投稿されたため、受け付けられませんでした。時間をおいてもう一度お試しください"


def client_ip(request):
    """投稿元のIPアドレスを返す。

    Railway上では、アプリに届く接続元(REMOTE_ADDR)はRailwayの中継サーバーになる。Railwayの中継サーバーは
    利用者が送ってきたX-Forwarded-Forを取り除き、実際の接続元を先頭に入れて渡すため、その先頭の値を使う。
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if settings.IS_RAILWAY and forwarded:
        return forwarded.split(",")[0].strip()
    return request.META["REMOTE_ADDR"]


def reserve_answer_post(request, problem):
    """同じIPアドレスから同じ問題への直近10分間の投稿が上限未満なら、今回の投稿を記録してTrueを返す。"""
    ip_address = client_ip(request)
    logs = AnswerPostLog.objects.filter(ip_address=ip_address, problem=problem)
    logs.filter(created_at__lte=timezone.now() - ANSWER_POST_WINDOW).delete()
    if logs.count() >= ANSWER_POST_LIMIT:
        return False
    AnswerPostLog.objects.create(ip_address=ip_address, problem=problem)
    return True


# 締切までの残り表示(詳細設計書 2a・2c「2.2 表示項目」)。回答投稿画面と受付中の問題一覧で使う
def remaining_label(deadline):
    """締切までの残りを「N日」(24時間以上)/「N時間」(1時間以上)/「N分」(1時間未満)で返す。

    端数は切り捨てる。1分未満は「1分」とする(締切前なのに「0分」と表示しないため)。
    """
    seconds = (deadline - timezone.now()).total_seconds()
    if seconds <= 0:
        return None
    if seconds >= 24 * 3600:
        return f"{int(seconds // (24 * 3600))}日"
    if seconds >= 3600:
        return f"{int(seconds // 3600)}時間"
    return f"{max(1, int(seconds // 60))}分"
