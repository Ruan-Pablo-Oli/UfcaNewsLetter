"""Views do projeto: entrega da SPA construída (React/Vite)."""
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.template import TemplateDoesNotExist

_SEM_BUILD = """<!doctype html>
<html lang="pt-br"><meta charset="utf-8">
<title>UFCA Newsletter — front não construído</title>
<h1>UFCA Newsletter</h1>
<p>A API está no ar, mas o front ainda não foi construído nesta instância.</p>
<p>Em desenvolvimento, use o servidor do Vite: <code>cd frontend &amp;&amp; npm run dev</code>.</p>
<p>Para servir o front por aqui: <code>npm run build</code> e reconstrua a imagem.</p>
"""


def spa(request):
    """Entrega o `index.html` da SPA; o roteamento fica com o React Router.

    Qualquer caminho que não seja de uma rota do Django cai aqui, para que
    recarregar a página em `/busca` (por exemplo) funcione como no servidor de
    desenvolvimento do Vite.
    """
    if not settings.SPA_DIR.is_dir():
        return HttpResponse(_SEM_BUILD, status=200)
    try:
        return render(request, "index.html")
    except TemplateDoesNotExist:
        return HttpResponse(_SEM_BUILD, status=200)
