from django.http import HttpResponse
from django.urls import path


def deploy_check(request):
    return HttpResponse("dokoutsu: Railway deploy test OK")


urlpatterns = [
    path("", deploy_check),
]
