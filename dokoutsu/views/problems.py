"""4a 問題投稿画面、2c 受付中の問題一覧、2d 受付終了の問題一覧(詳細設計書 4a・2c・2d)"""

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.db.models.functions import Coalesce
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from ..forms import ProblemForm
from ..models import Problem
from ..services import remaining_label


def _answer_url(request, problem):
    return request.build_absolute_uri(reverse("answer_create", kwargs={"pk": problem.pk}))


# --- 4a 問題投稿画面 ---


@login_required
def problem_new_view(request):
    if request.method == "POST":
        form = ProblemForm(request.POST)
        if form.is_valid():
            # commit=False: フォームの内容から問題を作るが、まだ保存しない。出題者を入れてから保存する
            problem = form.save(commit=False)
            problem.author = request.user
            problem.save()
            return redirect("problem_created", pk=problem.pk)
    else:
        form = ProblemForm()
    return render(request, "problems/new.html", {"form": form, "show_back": True})


@login_required
def problem_created_view(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    if problem.author_id != request.user.id:
        raise Http404
    return render(
        request,
        "problems/created.html",
        {
            "problem": problem,
            "answer_count": problem.answer_posts.count(),
            "answer_url": _answer_url(request, problem),
            "show_back": True,
        },
    )


# --- 2c / 2d 問題一覧 ---


@login_required
def active_problems_view(request):
    problems = list(
        Problem.objects.filter(
            author=request.user, closed_at__isnull=True, deadline__gt=timezone.now()
        )
        # annotate: 問題ごとの回答数(answer_count)を、問題の取得と同じ1回の問い合わせで数えて付け加える
        .annotate(answer_count=Count("answer_posts"))
        .order_by("deadline")
    )
    for problem in problems:
        problem.remaining = remaining_label(problem.deadline)
        problem.share_url = _answer_url(request, problem)
    return render(request, "problems/active.html", {"problems": problems})


@login_required
def archive_problems_view(request):
    problems = list(
        Problem.objects.filter(author=request.user)
        .filter(Q(closed_at__isnull=False) | Q(deadline__lte=timezone.now()))
        .annotate(answer_count=Count("answer_posts"))
        # 終了日時の新しい順。締切前に受付終了した問題はclosed_at、それ以外はdeadlineを終了日時とする
        # (Coalesce: 並べた項目のうち、最初に値が入っているものを使う)
        .order_by(Coalesce("closed_at", "deadline").desc())
    )
    for problem in problems:
        problem.share_url = _answer_url(request, problem)
    return render(
        request, "problems/archive.html", {"problems": problems, "show_back": True}
    )


@login_required
def problem_close_view(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    problem = get_object_or_404(Problem, pk=pk)
    if problem.author_id != request.user.id:
        raise Http404
    if problem.closed_at is None:
        problem.closed_at = timezone.now()
        problem.save(update_fields=["closed_at"])
    return redirect("active_problems")


@login_required
def problem_delete_view(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    problem = get_object_or_404(Problem, pk=pk)
    if problem.author_id != request.user.id:
        raise Http404
    next_url = request.POST.get("next", "active_problems")
    problem.delete()
    return redirect(next_url if next_url in ("active_problems", "archive_problems") else "active_problems")
