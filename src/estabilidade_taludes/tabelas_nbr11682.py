"""Tabelas normativas da ABNT NBR 11682:2009 e constantes trigonométricas racionais.

LOFRANO TECNOLOGIA.
Todos os coeficientes e constantes operam em frações racionais exatas (Fraction).
"""

from fractions import Fraction
import math
from typing import Dict, NamedTuple


class NivelSegurancaNBR11682(NamedTuple):
    """Nível de segurança e fator de segurança mínimo da NBR 11682 (Tabela 1)."""
    codigo: str
    descricao: str
    fs_minimo_numerador: int
    fs_minimo_denominador: int

    @property
    def fs_minimo_fracao(self) -> Fraction:
        return Fraction(self.fs_minimo_numerador, self.fs_minimo_denominador)


class TipoSoloReferencia(NamedTuple):
    """Parâmetros geotécnicos típicos de solos brasileiros para referência."""
    codigo: str
    nome: str
    peso_especifico_kn_m3: int       # kN/m³ inteiros
    coesao_efetiva_kpa: int          # kPa inteiros
    angulo_atrito_graus: int         # Graus inteiros


NIVEIS_SEGURANCA: Dict[str, NivelSegurancaNBR11682] = {
    "ALTO": NivelSegurancaNBR11682(
        codigo="ALTO",
        descricao="Alto risco de perdas de vidas humanas ou danos patrimoniais/ambientais graves",
        fs_minimo_numerador=3,
        fs_minimo_denominador=2,  # FS >= 1,50
    ),
    "MEDIO": NivelSegurancaNBR11682(
        codigo="MEDIO",
        descricao="Médio risco, áreas com ocupação esporádica ou danos materiais moderados",
        fs_minimo_numerador=7,
        fs_minimo_denominador=5,  # FS >= 1,40
    ),
    "BAIXO": NivelSegurancaNBR11682(
        codigo="BAIXO",
        descricao="Baixo risco, áreas desabitadas, taludes provisórios sem estruturas",
        fs_minimo_numerador=13,
        fs_minimo_denominador=10,  # FS >= 1,30
    ),
}

SOLOS_REFERENCIA: Dict[str, TipoSoloReferencia] = {
    "ARGILA_MOLE": TipoSoloReferencia("ARGILA_MOLE", "Argila mole saturada", 16, 12, 18),
    "ARGILA_MEDIA": TipoSoloReferencia("ARGILA_MEDIA", "Argila siltosa média", 18, 25, 24),
    "ARGILA_RIJA": TipoSoloReferencia("ARGILA_RIJA", "Argila rija / saprolítica", 19, 40, 28),
    "SILTE_ARENOSO": TipoSoloReferencia("SILTE_ARENOSO", "Silte arenoso residual", 18, 15, 30),
    "AREIA_SILTOSA": TipoSoloReferencia("AREIA_SILTOSA", "Areia siltosa medianamente compacta", 19, 5, 32),
    "AREIA_COMPACTA": TipoSoloReferencia("AREIA_COMPACTA", "Areia pura ou com pedregulhos compacta", 20, 0, 36),
}

# Tabela pré-computada de seno, cosseno e tangente para graus inteiros de 0 a 89
# expressos como Fraction com precisão de 10^8 (8 casas decimais exatas)
# Previne qualquer uso de IEEE-754 float em tempo de execução
TABELA_SENO_GRAUS: Dict[int, Fraction] = {}
TABELA_COSSENO_GRAUS: Dict[int, Fraction] = {}
TABELA_TANGENTE_GRAUS: Dict[int, Fraction] = {}

for _grau in range(91):
    _rad = math.radians(_grau)
    _s_int = round(math.sin(_rad) * 100_000_000)
    _c_int = round(math.cos(_rad) * 100_000_000)
    TABELA_SENO_GRAUS[_grau] = Fraction(_s_int, 100_000_000)
    TABELA_COSSENO_GRAUS[_grau] = Fraction(_c_int, 100_000_000)
    if _grau < 90:
        _t_int = round(math.tan(_rad) * 100_000_000)
        TABELA_TANGENTE_GRAUS[_grau] = Fraction(_t_int, 100_000_000)
    else:
        TABELA_TANGENTE_GRAUS[_grau] = Fraction(999_999_999, 1)


def obter_seno_graus_racional(graus: int) -> Fraction:
    """Retorna o seno exato em fração racional para ângulo inteiro em graus."""
    sinal = -1 if graus < 0 else 1
    g = abs(graus) % 360
    if g <= 90:
        return sinal * TABELA_SENO_GRAUS[g]
    elif g <= 180:
        return sinal * TABELA_SENO_GRAUS[180 - g]
    elif g <= 270:
        return -sinal * TABELA_SENO_GRAUS[g - 180]
    else:
        return -sinal * TABELA_SENO_GRAUS[360 - g]


def obter_cosseno_graus_racional(graus: int) -> Fraction:
    """Retorna o cosseno exato em fração racional para ângulo inteiro em graus."""
    g = abs(graus) % 360
    if g <= 90:
        return TABELA_COSSENO_GRAUS[g]
    elif g <= 180:
        return -TABELA_COSSENO_GRAUS[180 - g]
    elif g <= 270:
        return -TABELA_COSSENO_GRAUS[g - 180]
    else:
        return TABELA_COSSENO_GRAUS[360 - g]


def obter_tangente_graus_racional(graus: int) -> Fraction:
    """Retorna a tangente exata em fração racional para ângulo inteiro em graus."""
    sinal = -1 if graus < 0 else 1
    g = abs(graus) % 180
    if g > 90:
        g = 180 - g
        sinal = -sinal
    return sinal * TABELA_TANGENTE_GRAUS[min(g, 90)]
