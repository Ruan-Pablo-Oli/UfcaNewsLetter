from .calendario import CalendarioCollector, CalendarioEventRecord
from .concursos_selecoes import ConcursoRecord, ConcursosSelecoesCollector
from .noticias_informes import CollectionError, NewsInformeCollector, NewsInformeRecord

__all__ = [
    "CalendarioCollector",
    "CalendarioEventRecord",
    "CollectionError",
    "ConcursoRecord",
    "ConcursosSelecoesCollector",
    "NewsInformeCollector",
    "NewsInformeRecord",
]
