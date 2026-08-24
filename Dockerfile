# --- estágio 1: build da SPA ---------------------------------------------
# O bundle é gerado na imagem para que a aplicação sirva o front já pronto,
# sem depender de um `npm run build` na máquina de quem sobe o projeto.
FROM node:22-slim AS frontend

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- estágio 2: aplicação -------------------------------------------------
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY docker/scheduler.sh /usr/local/bin/scheduler.sh
RUN chmod +x /usr/local/bin/scheduler.sh

WORKDIR /app
COPY app/ /app/
COPY --from=frontend /frontend/dist/ /app/spa/

# Estáticos coletados na imagem: o contêiner sobe pronto para servir, e o
# collectstatic não precisa de banco.
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput --clear

EXPOSE 8000

# Gunicorn no lugar do runserver: o servidor de desenvolvimento do Django não é
# feito para produção (thread única, sem robustez, avisa isso no próprio log).
CMD ["gunicorn", "ufcanewsletter.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
