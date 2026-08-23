"""URL configuration for the newsletter app."""
from django.urls import path

from . import views, views_fontes

urlpatterns = [
    path("feed/", views.feed, name="feed"),
    path("feedback/", views.feedback, name="feedback"),
    path("feedback/historico/", views.feedback_historico, name="feedback_historico"),
    path("busca/", views.busca, name="busca"),
    path("historico/", views.historico, name="historico"),
    path("fontes/criar/", views_fontes.criar_fonte, name="fonte_criar"),
    path("fontes/<int:fonte_id>/", views_fontes.editar_fonte, name="fonte_editar"),
    path("fontes/<int:fonte_id>/remover/", views_fontes.remover_fonte, name="fonte_remover"),
    path("fontes/", views_fontes.listar_fontes, name="fontes"),
]
