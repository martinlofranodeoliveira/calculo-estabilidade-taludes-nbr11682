"""Modelos de dados e validações de domínio para estabilidade de taludes NBR 11682.

LOFRANO TECNOLOGIA.
Todos os dados e resultados operam estritamente em inteiros e frações racionais exatas.
"""

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Dict, List, Optional

from .errors import ErroValidacaoGeotecnica, ERR_VALIDACAO_DOMINIO
from .tabelas_nbr11682 import NIVEIS_SEGURANCA


@dataclass(frozen=True)
class Ponto2D:
    """Coordenada bidimensional (X, Y) do perfil topográfico em milímetros inteiros."""
    x_mm: int
    y_mm: int

    def __post_init__(self):
        if not isinstance(self.x_mm, int) or not isinstance(self.y_mm, int):
            raise ErroValidacaoGeotecnica("Coordenadas devem ser inteiros em milímetros.", ERR_VALIDACAO_DOMINIO)


@dataclass(frozen=True)
class PropriedadesSolo:
    """Parâmetros de resistência ao cisalhamento e peso do maciço terroso (Mohr-Coulomb)."""
    nome_camada: str
    peso_especifico_n_m3: int       # Peso específico natural em N/m³ (ex: 18000 N/m³ = 18 kN/m³)
    coesao_efetiva_pa: int          # Coesão efetiva c' em Pascals (ex: 15000 Pa = 15 kPa)
    angulo_atrito_graus: int         # Ângulo de atrito interno phi' em graus inteiros (0 a 45)

    def __post_init__(self):
        if not self.nome_camada or not isinstance(self.nome_camada, str):
            raise ErroValidacaoGeotecnica("Nome da camada de solo deve ser fornecido.", ERR_VALIDACAO_DOMINIO)
        if not isinstance(self.peso_especifico_n_m3, int) or self.peso_especifico_n_m3 <= 0:
            raise ErroValidacaoGeotecnica("Peso específico deve ser inteiro positivo em N/m³.", ERR_VALIDACAO_DOMINIO)
        if not isinstance(self.coesao_efetiva_pa, int) or self.coesao_efetiva_pa < 0:
            raise ErroValidacaoGeotecnica("Coesão efetiva deve ser inteiro não-negativo em Pascals.", ERR_VALIDACAO_DOMINIO)
        if not isinstance(self.angulo_atrito_graus, int) or not (0 <= self.angulo_atrito_graus <= 45):
            raise ErroValidacaoGeotecnica("Ângulo de atrito deve ser inteiro entre 0 e 45 graus.", ERR_VALIDACAO_DOMINIO)


@dataclass(frozen=True)
class CirculoRuptura:
    """Geometria da superfície de deslizamento cilíndrica hipotética."""
    centro_x_mm: int
    centro_y_mm: int
    raio_mm: int

    def __post_init__(self):
        if not isinstance(self.raio_mm, int) or self.raio_mm <= 0:
            raise ErroValidacaoGeotecnica("Raio do círculo de ruptura deve ser inteiro positivo em mm.", ERR_VALIDACAO_DOMINIO)


@dataclass(frozen=True)
class TaludeInput:
    """Especificação completa do talude, geometria, solo e círculo crítico."""
    nome_talude: str
    descricao: str
    nivel_seguranca_nbr11682: str
    perfil_terreno: List[Ponto2D]
    circulo_tentativa: CirculoRuptura
    solo: PropriedadesSolo
    numero_fatias: int = 10
    nivel_dagua_y_mm: Optional[int] = None
    sobrecarga_crista_pa: int = 0

    def __post_init__(self):
        if not self.nome_talude or not isinstance(self.nome_talude, str):
            raise ErroValidacaoGeotecnica("Nome do talude deve ser informado.", ERR_VALIDACAO_DOMINIO)
        if self.nivel_seguranca_nbr11682 not in NIVEIS_SEGURANCA:
            raise ErroValidacaoGeotecnica(
                f"Nível de segurança inválido: '{self.nivel_seguranca_nbr11682}'. Use ALTO, MEDIO ou BAIXO.",
                ERR_VALIDACAO_DOMINIO,
            )
        if len(self.perfil_terreno) < 2:
            raise ErroValidacaoGeotecnica("O perfil do terreno deve conter pelo menos 2 pontos topográficos.", ERR_VALIDACAO_DOMINIO)
        # O perfil do terreno deve ter coordenadas X estritamente crescentes
        for i in range(len(self.perfil_terreno) - 1):
            if self.perfil_terreno[i].x_mm >= self.perfil_terreno[i + 1].x_mm:
                raise ErroValidacaoGeotecnica("Os pontos do perfil do terreno devem ter coordenadas X estritamente crescentes.", ERR_VALIDACAO_DOMINIO)
        if not isinstance(self.numero_fatias, int) or not (4 <= self.numero_fatias <= 100):
            raise ErroValidacaoGeotecnica("O número de fatias (lamelas) deve ser entre 4 e 100.", ERR_VALIDACAO_DOMINIO)


@dataclass(frozen=True)
class FatiaDiscretizada:
    """Dados geométricos e forças atuantes e resistentes em uma fatia individual."""
    indice: int
    x_central_mm: int
    largura_mm: int
    y_topo_mm: int
    y_base_mm: int
    altura_media_mm: int
    inclinacao_base_graus: int
    peso_fatia_n: int
    poropressao_base_pa: int
    forca_atuante_tangencial_n: int
    forca_resistente_fellenius_n: int


@dataclass(frozen=True)
class ResultadoEstabilidade:
    """Relatório consolidado de estabilidade pelos métodos de Fellenius e Bishop Simplificado."""
    nome_talude: str
    descricao: str
    nivel_seguranca: str
    fs_minimo_exigido: Fraction
    fator_seguranca_fellenius: Fraction
    fator_seguranca_bishop: Fraction
    peso_total_maciço_n: int
    momento_atuante_total_nm: int
    momento_resistente_fellenius_nm: int
    momento_resistente_bishop_nm: int
    fatias: List[FatiaDiscretizada]
    conforme_nbr11682: bool
    diagnostico: str
    iteracoes_bishop: int


def formatar_fracao_decimal(frac: Fraction, casas: int = 3) -> str:
    """Converte fração racional para string decimal exata em formato pt-BR (ex: Fraction(3, 2) -> '1,500')."""
    if frac.denominator == 0:
        return "N/A"
    sinal = "-" if frac < 0 else ""
    num_abs = abs(frac.numerator)
    den_abs = abs(frac.denominator)
    fator = 10 ** casas
    valor_arredondado = (num_abs * fator * 2 + den_abs) // (den_abs * 2)
    parte_inteira = valor_arredondado // fator
    parte_decimal = valor_arredondado % fator
    return f"{sinal}{parte_inteira},{parte_decimal:0{casas}d}"


def formatar_comprimento_m(milimetros: int) -> str:
    """Converte milímetros para metros em pt-BR (ex: 12000 -> 12,00 m)."""
    sinal = "-" if milimetros < 0 else ""
    v_abs = abs(milimetros)
    m = v_abs // 1000
    resto = v_abs % 1000
    cm = resto // 10
    return f"{sinal}{m},{cm:02d} m"


def formatar_pressao_kpa(pascals: int) -> str:
    """Converte Pascals para kPa em pt-BR (ex: 15000 -> 15,00 kPa)."""
    sinal = "-" if pascals < 0 else ""
    v_abs = abs(pascals)
    kpa = v_abs // 1000
    resto = v_abs % 1000
    cent = resto // 10
    return f"{sinal}{kpa},{cent:02d} kPa"


def formatar_forca_kn(newtons: int) -> str:
    """Converte Newtons para kN em pt-BR (ex: 125000 -> 125,00 kN)."""
    sinal = "-" if newtons < 0 else ""
    v_abs = abs(newtons)
    kn = v_abs // 1000
    resto = v_abs % 1000
    cent = resto // 10
    return f"{sinal}{kn},{cent:02d} kN"
