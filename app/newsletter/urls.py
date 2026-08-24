"""URL configuration for the newsletter app."""
from django.urls import path

from . import views, views_fontes, views_revisao

urlpatterns = [
    path("feed/", views.feed, name="feed"),
    path("feedback/", views.feedback, name="feedback"),
    path("feedback/historico/", views.feedback_historico, name="feedback_historico"),
    path("feedback/<int:conteudo_id>/", views.feedback_remover, name="feedback_remover"),
    path("busca/", views.busca, name="busca"),
    path("historico/", views.historico, name="historico"),
    path("fontes/criar/", views_fontes.criar_fonte, name="fonte_criar"),
    path("fontes/<int:fonte_id>/", views_fontes.editar_fonte, name="fonte_editar"),
    path("fontes/<int:fonte_id>/remover/", views_fontes.remover_fonte, name="fonte_remover"),
    path("fontes/", views_fontes.listar_fontes, name="fontes"),
    path("revisao/", views_revisao.fila_revisao, name="revisao"),
    path("revisao/<int:conteudo_id>/aprovar/", views_revisao.aprovar, name="revisao_aprovar"),
    path("revisao/<int:conteudo_id>/descartar/", views_revisao.descartar, name="revisao_descartar"),
    path(
        "revisao/<int:conteudo_id>/reclassificar/",
        views_revisao.reclassificar,
        name="revisao_reclassificar",
    ),
]
