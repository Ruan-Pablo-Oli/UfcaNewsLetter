"""URL configuration for the newsletter app."""
from django.urls import path

from . import views, views_revisao

urlpatterns = [
    path("feed/", views.feed, name="feed"),
    path("feedback/", views.feedback, name="feedback"),
    path("feedback/historico/", views.feedback_historico, name="feedback_historico"),
    path("busca/", views.busca, name="busca"),
    path("historico/", views.historico, name="historico"),
    path("revisao/", views_revisao.fila_revisao, name="revisao"),
    path("revisao/<int:conteudo_id>/aprovar/", views_revisao.aprovar, name="revisao_aprovar"),
    path("revisao/<int:conteudo_id>/descartar/", views_revisao.descartar, name="revisao_descartar"),
    path(
        "revisao/<int:conteudo_id>/reclassificar/",
        views_revisao.reclassificar,
        name="revisao_reclassificar",
    ),
]
