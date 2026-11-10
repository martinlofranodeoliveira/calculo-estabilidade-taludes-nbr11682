"""Cálculo Determinístico de Estabilidade de Taludes e Encostas (ABNT NBR 11682:2009).

LOFRANO TECNOLOGIA.
Aritmética inteira e racional exata (Zero Float) com métodos de Fellenius e Bishop Simplificado.
"""

from .calculator import calcular_estabilidade_talude
from .codecs import codificar_resultado_json_str, decodificar_talude_json_str
from .domain import (
    CirculoRuptura,
    FatiaDiscretizada,
    Ponto2D,
    PropriedadesSolo,
    ResultadoEstabilidade,
    TaludeInput,
    formatar_comprimento_m,
    formatar_forca_kn,
    formatar_fracao_decimal,
    formatar_pressao_kpa,
)
from .errors import (
    ErroConvergenciaBishop,
    ErroEstabilidadeTalude,
    ErroExportacao,
    ErroGeometriaCirculo,
    ErroValidacaoGeotecnica,
)
from .exports import (
    criar_pacote_zip_deterministico,
    gerar_fatias_csv_str,
    gerar_laudo_geotecnico_markdown,
    gerar_resumo_csv_str,
)
from .svg_report import gerar_svg_estabilidade
from .tabelas_nbr11682 import NIVEIS_SEGURANCA, SOLOS_REFERENCIA

__version__ = "1.0.0"

__all__ = [
    "CirculoRuptura",
    "ErroConvergenciaBishop",
    "ErroEstabilidadeTalude",
    "ErroExportacao",
    "ErroGeometriaCirculo",
    "ErroValidacaoGeotecnica",
    "FatiaDiscretizada",
    "NIVEIS_SEGURANCA",
    "Ponto2D",
    "PropriedadesSolo",
    "ResultadoEstabilidade",
    "SOLOS_REFERENCIA",
    "TaludeInput",
    "calcular_estabilidade_talude",
    "codificar_resultado_json_str",
    "criar_pacote_zip_deterministico",
    "decodificar_talude_json_str",
    "formatar_comprimento_m",
    "formatar_forca_kn",
    "formatar_fracao_decimal",
    "formatar_pressao_kpa",
    "gerar_fatias_csv_str",
    "gerar_laudo_geotecnico_markdown",
    "gerar_resumo_csv_str",
    "gerar_svg_estabilidade",
]
