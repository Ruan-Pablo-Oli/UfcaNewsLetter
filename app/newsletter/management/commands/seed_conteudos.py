"""Popula o banco com conteúdos fictícios para desenvolvimento e demonstração.

Sem o coletor automático (US-03.1, issue #16) o feed nasce vazio em qualquer
clone novo do repositório, o que impede exercitar a personalização (#14), o
ajuste de relevância (#15) e a tela de feed (#47). Este comando cria fontes,
categorias e conteúdos de exemplo cobrindo os três caminhos do algoritmo de
`newsletter/feed.py`: conteúdo universal, direcionado por curso e direcionado
por interesse.

Idempotente (usa `get_or_create` com `hash_dedup` derivado do título): pode ser
executado várias vezes sem duplicar. **Não** é chamado automaticamente na subida
dos contêineres — são dados falsos, e rodá-lo é uma decisão explícita
(`make seed-demo`).
"""
import hashlib
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from newsletter.models import Categoria, Conteudo, Fonte, Interesse

FONTES = {
    "portal": {
        "nome": "Portal UFCA",
        "tipo": Fonte.Tipo.HTML,
        "url": "https://www.ufca.edu.br/noticias/",
        "intervalo_coleta": 60,
    },
    "prograd": {
        "nome": "PROGRAD — Editais",
        "tipo": Fonte.Tipo.PDF,
        "url": "https://www.ufca.edu.br/prograd/editais/",
        "intervalo_coleta": 180,
    },
    "calendario": {
        "nome": "Calendário Acadêmico UFCA",
        "tipo": Fonte.Tipo.CALENDARIO,
        "url": "https://www.ufca.edu.br/calendario-academico/",
        "intervalo_coleta": 1440,
    },
}

# (titulo, resumo, categoria, fonte, dias_atras, universal, cursos, interesses)
CONTEUDOS = [
    (
        "Matrícula institucional 2026.2 abre na próxima segunda",
        "Todos os discentes devem realizar a matrícula institucional pelo SIGAA "
        "entre os dias 3 e 7 de agosto.",
        Categoria.Tipo.PRAZO,
        "calendario",
        0,
        True,
        [],
        ["Calendário Acadêmico"],
    ),
    (
        "Restaurante Universitário funcionará em horário reduzido",
        "Por conta da manutenção da rede elétrica, o RU do campus Juazeiro do "
        "Norte servirá apenas almoço nesta quinta-feira.",
        Categoria.Tipo.COMUNICADO,
        "portal",
        1,
        True,
        [],
        ["Restaurante Universitário"],
    ),
    (
        "Edital PRAE nº 12/2026 — Auxílio Moradia",
        "Inscrições abertas para o auxílio moradia do semestre 2026.2. "
        "Documentação deve ser enviada pelo SIGAA até 20 de agosto.",
        Categoria.Tipo.EDITAL,
        "prograd",
        2,
        True,
        [],
        ["Editais", "Bolsas"],
    ),
    (
        "Calendário de férias docentes é divulgado",
        "A PROGRAD publicou o período de recesso docente e o impacto nas "
        "atividades de ensino.",
        Categoria.Tipo.COMUNICADO,
        "calendario",
        4,
        True,
        [],
        ["Calendário Acadêmico"],
    ),
    (
        "Semana Universitária 2026 tem inscrições abertas",
        "Programação com minicursos, palestras e apresentações de trabalhos em "
        "todos os campi. Inscrições gratuitas.",
        Categoria.Tipo.EVENTO,
        "portal",
        5,
        True,
        [],
        ["Eventos", "Extensão"],
    ),
    (
        "Edital de Monitoria 2026.2 — Ciência da Computação",
        "Seleção de monitores para as disciplinas de Algoritmos, Estrutura de "
        "Dados e Banco de Dados. Bolsa de R$ 400,00.",
        Categoria.Tipo.EDITAL,
        "prograd",
        1,
        False,
        ["ciencia_da_computacao", "engenharia_de_software"],
        ["Monitoria", "Bolsas"],
    ),
    (
        "Hackathon UFCA: inscrições para equipes de tecnologia",
        "Maratona de 48 horas com desafios propostos por empresas da região do "
        "Cariri. Equipes de 3 a 5 pessoas.",
        Categoria.Tipo.EVENTO,
        "portal",
        3,
        False,
        ["ciencia_da_computacao", "engenharia_de_software", "sistemas_de_informacao"],
        ["Eventos"],
    ),
    (
        "Vagas de estágio em desenvolvimento de software no Cariri",
        "Cinco vagas para estágio remunerado com bolsa de R$ 1.200,00 e "
        "auxílio-transporte. Requisito: a partir do 4º período.",
        Categoria.Tipo.COMUNICADO,
        "portal",
        2,
        False,
        ["ciencia_da_computacao", "engenharia_de_software", "sistemas_de_informacao"],
        ["Estágios"],
    ),
    (
        "Defesa de TCC: aplicações de aprendizado de máquina na agricultura",
        "Sessão pública de defesa no auditório do bloco didático, aberta a toda "
        "a comunidade acadêmica.",
        Categoria.Tipo.EVENTO,
        "portal",
        6,
        False,
        ["ciencia_da_computacao", "agronomia"],
        ["Eventos"],
    ),
    (
        "Edital PIBIC 2026/2027 — Iniciação Científica",
        "Submissão de planos de trabalho para bolsas de iniciação científica "
        "CNPq e FUNCAP. Prazo final: 30 de agosto.",
        Categoria.Tipo.EDITAL,
        "prograd",
        3,
        False,
        [],
        ["Iniciação Científica", "Bolsas", "Editais"],
    ),
    (
        "Prazo para entrega do relatório parcial de bolsistas",
        "Bolsistas de iniciação científica devem entregar o relatório parcial "
        "até o dia 15 deste mês, sob pena de suspensão da bolsa.",
        Categoria.Tipo.PRAZO,
        "prograd",
        7,
        False,
        [],
        ["Iniciação Científica", "Bolsas"],
    ),
    (
        "Chamada para projetos de extensão universitária",
        "Editais de fluxo contínuo para registro de ações de extensão junto às "
        "comunidades do Cariri.",
        Categoria.Tipo.EDITAL,
        "prograd",
        8,
        False,
        [],
        ["Extensão", "Editais"],
    ),
    (
        "Simpósio de Direito e Cidadania recebe inscrições",
        "Três dias de mesas-redondas sobre acesso à justiça, com certificação "
        "de 20 horas complementares.",
        Categoria.Tipo.EVENTO,
        "portal",
        4,
        False,
        ["direito"],
        ["Eventos"],
    ),
    (
        "Estágio supervisionado em escritório-escola: seleção aberta",
        "Vagas para discentes de Direito a partir do 6º período no Núcleo de "
        "Prática Jurídica.",
        Categoria.Tipo.EDITAL,
        "prograd",
        5,
        False,
        ["direito"],
        ["Estágios", "Editais"],
    ),
    (
        "Mutirão de atendimento em saúde no Crato",
        "Ação de extensão com atendimentos de enfermagem, nutrição e "
        "fisioterapia à população do bairro Seminário.",
        Categoria.Tipo.EVENTO,
        "portal",
        2,
        False,
        ["enfermagem", "nutricao", "fisioterapia", "medicina"],
        ["Extensão", "Eventos"],
    ),
    (
        "Edital de campo de estágio em unidades básicas de saúde",
        "Distribuição de vagas de estágio obrigatório nas UBS conveniadas de "
        "Juazeiro do Norte, Crato e Barbalha.",
        Categoria.Tipo.EDITAL,
        "prograd",
        6,
        False,
        ["enfermagem", "medicina", "biomedicina", "odontologia"],
        ["Estágios", "Editais"],
    ),
    (
        "Prazo de entrega do relatório de estágio obrigatório",
        "Discentes em estágio obrigatório devem protocolar o relatório final "
        "com o supervisor até o fim do mês.",
        Categoria.Tipo.PRAZO,
        "prograd",
        9,
        False,
        [],
        ["Estágios"],
    ),
    (
        "Concurso público para técnico-administrativo em educação",
        "Edital com 18 vagas para os campi de Juazeiro do Norte, Crato, "
        "Barbalha e Brejo Santo.",
        Categoria.Tipo.EDITAL,
        "portal",
        10,
        True,
        [],
        ["Concursos e Seleções", "Editais"],
    ),
    (
        "Seleção de professor substituto — Engenharia Civil",
        "Vaga para a área de estruturas, com inscrições pelo sistema de "
        "concursos da UFCA.",
        Categoria.Tipo.EDITAL,
        "prograd",
        11,
        False,
        ["engenharia_civil", "arquitetura_e_urbanismo"],
        ["Concursos e Seleções"],
    ),
    (
        "Visita técnica a canteiro de obras em Barbalha",
        "Atividade prática para discentes de Engenharia Civil e Arquitetura, "
        "com transporte fornecido pela universidade.",
        Categoria.Tipo.EVENTO,
        "portal",
        7,
        False,
        ["engenharia_civil", "arquitetura_e_urbanismo"],
        ["Eventos"],
    ),
    (
        "Mostra de projetos de Design do semestre",
        "Exposição dos trabalhos finais das disciplinas de projeto no hall do "
        "bloco de artes.",
        Categoria.Tipo.EVENTO,
        "portal",
        3,
        False,
        ["design"],
        ["Eventos", "Extensão"],
    ),
    (
        "Edital de apoio a participação em eventos científicos",
        "Auxílio financeiro para discentes com trabalho aceito em congressos "
        "nacionais e internacionais.",
        Categoria.Tipo.EDITAL,
        "prograd",
        12,
        True,
        [],
        ["Editais", "Bolsas", "Iniciação Científica"],
    ),
    (
        "Curso de extensão em metodologia científica",
        "Turma aberta a discentes de qualquer curso, com 40 horas e "
        "certificação.",
        Categoria.Tipo.EVENTO,
        "portal",
        8,
        False,
        [],
        ["Extensão", "Iniciação Científica"],
    ),
    (
        "Novo cardápio do Restaurante Universitário entra em vigor",
        "O cardápio do semestre inclui opções vegetarianas diárias em todos os "
        "campi.",
        Categoria.Tipo.COMUNICADO,
        "portal",
        5,
        True,
        [],
        ["Restaurante Universitário"],
    ),
    (
        "Prazo final para solicitação de trancamento de disciplinas",
        "Solicitações devem ser feitas pelo SIGAA e homologadas pela "
        "coordenação do curso.",
        Categoria.Tipo.PRAZO,
        "calendario",
        1,
        True,
        [],
        ["Calendário Acadêmico"],
    ),
    (
        "Seleção de monitores para laboratórios de Química",
        "Vagas de monitoria para as disciplinas experimentais de Química Geral "
        "e Orgânica.",
        Categoria.Tipo.EDITAL,
        "prograd",
        4,
        False,
        ["quimica", "farmacia", "biomedicina"],
        ["Monitoria", "Bolsas"],
    ),
    (
        "Semana de Administração debate empreendedorismo no Cariri",
        "Painéis com egressos e empresários locais sobre negócios na região.",
        Categoria.Tipo.EVENTO,
        "portal",
        6,
        False,
        ["administracao", "ciencias_economicas"],
        ["Eventos"],
    ),
    (
        "Estágio em gestão pública na prefeitura de Juazeiro do Norte",
        "Convênio abre dez vagas de estágio para discentes de Administração e "
        "áreas afins.",
        Categoria.Tipo.COMUNICADO,
        "portal",
        9,
        False,
        ["administracao", "ciencias_economicas", "servico_social"],
        ["Estágios"],
    ),
    (
        "Campanha de vacinação da comunidade acadêmica",
        "Postos de vacinação instalados nos quatro campi durante toda a "
        "semana.",
        Categoria.Tipo.COMUNICADO,
        "portal",
        13,
        True,
        [],
        [],
    ),
    (
        "Aulas de campo em Agronomia na Fazenda Experimental",
        "Cronograma de atividades práticas do semestre na unidade de Barbalha.",
        Categoria.Tipo.COMUNICADO,
        "portal",
        10,
        False,
        ["agronomia", "zootecnia", "ciencias_biologicas"],
        ["Calendário Acadêmico"],
    ),
]


def _hash_dedup(titulo):
    """Deriva um hash estável do título, imitando a dedup do coletor (#16)."""
    return hashlib.sha256(titulo.encode("utf-8")).hexdigest()


class Command(BaseCommand):
    help = "Popula o banco com conteúdos fictícios para desenvolvimento e demonstração."

    @transaction.atomic
    def handle(self, *args, **options):
        fontes = {
            chave: Fonte.objects.get_or_create(nome=dados["nome"], defaults=dados)[0]
            for chave, dados in FONTES.items()
        }
        categorias = {
            valor: Categoria.objects.get_or_create(nome=valor)[0]
            for valor in Categoria.Tipo.values
        }

        agora = timezone.now()
        novos = 0

        for (
            titulo,
            resumo,
            categoria,
            fonte,
            dias_atras,
            universal,
            cursos,
            interesses,
        ) in CONTEUDOS:
            conteudo, criado = Conteudo.objects.get_or_create(
                hash_dedup=_hash_dedup(titulo),
                defaults={
                    "titulo": titulo,
                    "corpo": resumo,
                    "resumo": resumo,
                    "data_publicacao": agora - timedelta(days=dias_atras),
                    "categoria": categorias[categoria],
                    "fonte": fontes[fonte],
                    "universal": universal,
                    "cursos": cursos,
                },
            )
            if not criado:
                continue

            novos += 1
            conteudo.interesses.set(
                Interesse.objects.get_or_create(nome=nome)[0] for nome in interesses
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Conteúdos de demonstração garantidos: {len(CONTEUDOS)} ({novos} novos)."
            )
        )
