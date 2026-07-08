"""Registro dos modelos do domínio no Django Admin."""
from django.contrib import admin

from .models import Categoria, Conteudo, Entrega, Feedback, Fonte, Interesse, Perfil


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("user", "curso", "periodo")
    search_fields = ("user__username", "curso")
    filter_horizontal = ("interesses",)


@admin.register(Interesse)
class InteresseAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome",)


@admin.register(Fonte)
class FonteAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "url", "intervalo_coleta")
    list_filter = ("tipo",)
    search_fields = ("nome", "url")


@admin.register(Conteudo)
class ConteudoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "fonte", "data_publicacao")
    list_filter = ("categoria", "fonte")
    search_fields = ("titulo", "corpo", "hash_dedup")


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ("conteudo", "usuario", "canal", "data_envio")
    list_filter = ("canal",)
    search_fields = ("conteudo__titulo", "usuario__username")


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("usuario", "conteudo", "tipo", "criado_em")
    list_filter = ("tipo",)
    search_fields = ("conteudo__titulo", "usuario__username")
