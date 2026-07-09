"""URL configuration for the newsletter app."""
from django.urls import path

from . import views

urlpatterns = [
    path("feed/", views.feed, name="feed"),
    path("feedback/", views.feedback, name="feedback"),
    path("feedback/historico/", views.feedback_historico, name="feedback_historico"),
]
