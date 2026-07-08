"""Views for ufcanewsletter project."""
from django.http import HttpResponse


def hello(request):
    return HttpResponse("Hello World")
