from django.contrib import admin

from .models import AnswerPost, Problem, Rank

admin.site.register(Rank)
admin.site.register(Problem)
admin.site.register(AnswerPost)
