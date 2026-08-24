#!/bin/sh
# Agendador das tarefas periódicas (ADR-008).
#
# Cada tarefa é um management command comum, e a decisão de "já é hora?" mora
# no próprio comando, não aqui: `coletar` respeita Fonte.intervalo_coleta,
# `enviar_digest` respeita Perfil.frequencia_email (1 ou 7 dias desde a última
# Entrega) e `notificar_push` deduplica por Entrega. Por isso o laço pode rodar
# num intervalo curto sem coletar demais nem mandar e-mail repetido — o
# intervalo define a *resolução* do agendamento, não a frequência das tarefas.
set -eu

INTERVALO="${SCHEDULER_INTERVALO_SEGUNDOS:-900}"

log() {
    echo "[scheduler $(date -u '+%Y-%m-%d %H:%M:%SZ')] $*"
}

# O serviço `web` aplica as migrações na subida; sem esperar, o primeiro ciclo
# quebraria contra um banco ainda sem tabelas.
log "aguardando as migrações..."
until python manage.py migrate --check >/dev/null 2>&1; do
    sleep 2
done

log "iniciando (intervalo de ${INTERVALO}s)"
while true; do
    for tarefa in coletar enviar_digest notificar_push; do
        log "executando: $tarefa"
        # Uma tarefa que falha (rede fora, SMTP recusando) não derruba as
        # demais nem o laço: o próximo ciclo tenta de novo.
        python manage.py "$tarefa" || log "FALHOU: $tarefa (segue o ciclo)"
    done
    log "ciclo concluído; dormindo ${INTERVALO}s"
    sleep "$INTERVALO"
done
