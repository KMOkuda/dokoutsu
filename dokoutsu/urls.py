from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="active_problems"), name="home"),
    path("signup", views.signup_view, name="signup"),
    path("signup/sent", views.signup_sent_view, name="signup_sent"),
    path("signup/activate/<uidb64>/<token>/", views.activate_view, name="activate"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("password_reset", views.password_reset_view, name="password_reset"),
    path(
        "password_reset/confirm/<uidb64>/<token>/",
        views.password_reset_confirm_view,
        name="password_reset_confirm",
    ),
    path("problems/new", views.problem_new_view, name="problem_new"),
    path(
        "problems/<uuid:pk>/created",
        views.problem_created_view,
        name="problem_created",
    ),
    path(
        "problems/<uuid:pk>/answer", views.answer_create_view, name="answer_create"
    ),
    path("problems/<uuid:pk>/close", views.problem_close_view, name="problem_close"),
    path(
        "problems/<uuid:pk>/delete", views.problem_delete_view, name="problem_delete"
    ),
    path("problems/active", views.active_problems_view, name="active_problems"),
    path("problems/archive", views.archive_problems_view, name="archive_problems"),
    path("problems/<uuid:pk>", views.answer_list_view, name="answer_list"),
]
