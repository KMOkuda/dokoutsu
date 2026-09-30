"""2a 回答投稿画面、2b 回答一覧画面(詳細設計書 2a・2b)"""

from django.shortcuts import get_object_or_404, render

from ..forms import AnswerPostForm
from ..models import AnswerPost, Problem
from ..services import (
    ANSWER_POST_LIMIT_MESSAGE,
    remaining_label,
    reserve_answer_post,
)


def answer_create_view(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    is_open = problem.is_open
    # 1つの問題に回答できるのは、同じブラウザから1回まで。回答済みかどうかはセッションで判定する
    # (詳細設計書 2a「7. この画面固有の設計事項」)。
    # answered_problems: 回答した問題の一覧(回答一覧の閲覧可否の判定にも使う)
    # my_answers: 問題ごとの自分の回答のID(回答済みの表示に使う)
    my_answer_id = request.session.get("my_answers", {}).get(str(problem.pk))
    answered = str(problem.pk) in request.session.get("answered_problems", [])
    form = None
    just_posted = False
    answered_error = None

    if request.method == "POST" and answered:
        answered_error = "この問題には回答済みです"
    elif request.method == "POST" and is_open:
        form = AnswerPostForm(request.POST, problem=problem)
        if form.is_valid() and not reserve_answer_post(request, problem):
            form.add_error(None, ANSWER_POST_LIMIT_MESSAGE)
        if form.is_valid():
            # commit=False: フォームの内容から回答を作るが、まだ保存しない。回答先の問題を入れてから保存する
            answer = form.save(commit=False)
            answer.problem = problem
            answer.save()
            request.session["answered_problems"] = [
                *request.session.get("answered_problems", []),
                str(problem.pk),
            ]
            request.session["my_answers"] = {
                **request.session.get("my_answers", {}),
                str(problem.pk): answer.pk,
            }
            answered = just_posted = True
            my_answer_id = answer.pk
    # 締切判定はサーバーがこのリクエストを受け取った時刻を基準に行う。受付中でなければフォームを出さない
    if form is None and not answered and is_open:
        form = AnswerPostForm(problem=problem)

    my_answer = (
        AnswerPost.objects.select_related("rank").filter(pk=my_answer_id, problem=problem).first()
        if answered and my_answer_id
        else None
    )
    return render(
        request,
        "problems/answer.html",
        {
            "problem": problem,
            "is_open": is_open,
            "form": form,
            "answered": answered,
            "just_posted": just_posted,
            "answered_error": answered_error,
            "my_answer": my_answer,
            "show_answer_list_link": answered
            and (problem.disclosure_type == Problem.AFTER_ANSWER or not is_open),
            "remaining": remaining_label(problem.deadline) if is_open else None,
            "show_back": True,
        },
    )


def answer_list_view(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    # 閲覧可否(詳細設計書 2b「3.2 閲覧可否の判定」): 出題者本人、受付終了後、
    # または回答後に公開の問題にこのブラウザで回答済み(セッションで判定)の場合に閲覧できる
    can_view = (
        (request.user.is_authenticated and problem.author_id == request.user.id)
        or not problem.is_open
        or (
            problem.disclosure_type == Problem.AFTER_ANSWER
            and str(problem.pk) in request.session.get("answered_problems", [])
        )
    )
    # select_related: 各回答の棋力(Rank)を回答と同じ1回の問い合わせでまとめて取得する
    answers = (
        problem.answer_posts.select_related("rank").order_by("-created_at") if can_view else []
    )
    return render(
        request,
        "answers/list.html",
        {
            "problem": problem,
            "can_view": can_view,
            "answers": answers,
            "show_back": True,
        },
    )
