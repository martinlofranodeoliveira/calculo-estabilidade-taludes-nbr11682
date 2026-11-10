"""Motor de cálculo determinístico de estabilidade de taludes (NBR 11682).

LOFRANO TECNOLOGIA.
Métodos de Fellenius e Bishop Simplificado operando 100% em aritmética inteira e frações racionais.
"""

from fractions import Fraction
import math
from typing import List, Tuple

from .domain import (
    CirculoRuptura,
    FatiaDiscretizada,
    Ponto2D,
    ResultadoEstabilidade,
    TaludeInput,
)
from .errors import (
    ErroConvergenciaBishop,
    ErroGeometriaCirculo,
    ERR_CIRCULO_INVALIDO,
    ERR_FALHA_CONVERGENCIA,
    ERR_RAIO_INSUFICIENTE,
)
from .tabelas_nbr11682 import (
    NIVEIS_SEGURANCA,
    TABELA_SENO_GRAUS,
    obter_cosseno_graus_racional,
    obter_seno_graus_racional,
    obter_tangente_graus_racional,
)


def obter_cota_terreno_mm(perfil: List[Ponto2D], x_mm: int) -> int:
    """Interpola a cota Y do perfil topográfico para uma abscissa X em mm."""
    if x_mm <= perfil[0].x_mm:
        return perfil[0].y_mm
    if x_mm >= perfil[-1].x_mm:
        return perfil[-1].y_mm

    for i in range(len(perfil) - 1):
        p1 = perfil[i]
        p2 = perfil[i + 1]
        if p1.x_mm <= x_mm <= p2.x_mm:
            dx = p2.x_mm - p1.x_mm
            dy = p2.y_mm - p1.y_mm
            if dx == 0:
                return p1.y_mm
            return p1.y_mm + (dy * (x_mm - p1.x_mm)) // dx

    return perfil[-1].y_mm


def graus_por_seno(seno_frac: Fraction) -> int:
    """Mapeia valor racional de seno para graus inteiros entre -90 e 90 sem usar ponto flutuante."""
    sinal = -1 if seno_frac < 0 else 1
    val = abs(seno_frac)
    if val >= Fraction(1, 1):
        return sinal * 90

    melhor_grau = 0
    menor_dif = abs(val - TABELA_SENO_GRAUS[0])
    for g in range(1, 91):
        dif = abs(val - TABELA_SENO_GRAUS[g])
        if dif < menor_dif:
            menor_dif = dif
            melhor_grau = g
        else:
            break
    return sinal * melhor_grau


def calcular_estabilidade_talude(projeto: TaludeInput) -> ResultadoEstabilidade:
    """Calcula o Fator de Segurança pelos métodos de Fellenius e Bishop Simplificado."""
    circ = projeto.circulo_tentativa
    r2 = circ.raio_mm ** 2

    # Encontrar intervalo de interseção [x_min, x_max] onde o círculo corta o terreno
    # O círculo deve estar contido entre centro_x - R e centro_x + R
    x_esq = max(circ.centro_x_mm - circ.raio_mm + 1, projeto.perfil_terreno[0].x_mm)
    x_dir = min(circ.centro_x_mm + circ.raio_mm - 1, projeto.perfil_terreno[-1].x_mm)

    if x_esq >= x_dir:
        raise ErroGeometriaCirculo(
            "Círculo de ruptura não intercepta o maciço dentro dos limites do perfil.",
            ERR_CIRCULO_INVALIDO,
        )

    # Buscar pontos reais de entrada e saída do círculo no maciço
    # Varredura em passos discretos de 100 mm
    pontos_corte: List[int] = []
    passo_busca = max(100, (x_dir - x_esq) // 200)
    for x in range(x_esq, x_dir, passo_busca):
        dx = x - circ.centro_x_mm
        val = r2 - dx ** 2
        if val < 0:
            continue
        y_circ = circ.centro_y_mm - math.isqrt(val)
        y_terr = obter_cota_terreno_mm(projeto.perfil_terreno, x)
        if y_circ < y_terr:
            pontos_corte.append(x)

    if not pontos_corte or len(pontos_corte) < 2:
        raise ErroGeometriaCirculo(
            "Círculo de ruptura encontra-se totalmente acima da superfície do terreno.",
            ERR_CIRCULO_INVALIDO,
        )

    x_inicio = pontos_corte[0]
    x_fim = pontos_corte[-1]
    extensao_x = x_fim - x_inicio

    if extensao_x < 1000:
        raise ErroGeometriaCirculo(
            "Extensão da superfície de ruptura é insuficiente para análise geotécnica.",
            ERR_RAIO_INSUFICIENTE,
        )

    num_fatias = projeto.numero_fatias
    largura_fatia = extensao_x // num_fatias

    fatias: List[FatiaDiscretizada] = []
    tan_phi = obter_tangente_graus_racional(projeto.solo.angulo_atrito_graus)
    c_solo = projeto.solo.coesao_efetiva_pa
    gamma = projeto.solo.peso_especifico_n_m3

    soma_atuante_num = 0
    soma_resistente_fellenius_num = 0
    peso_total_maciço = 0

    for idx in range(num_fatias):
        x_m = x_inicio + idx * largura_fatia + largura_fatia // 2
        dx = x_m - circ.centro_x_mm
        val_circ = r2 - dx ** 2
        if val_circ <= 0:
            continue
        y_base = circ.centro_y_mm - math.isqrt(val_circ)
        y_topo = obter_cota_terreno_mm(projeto.perfil_terreno, x_m)

        h_media = y_topo - y_base
        if h_media <= 0:
            continue

        # Ângulo de inclinação alfa da base da fatia
        sen_alfa_frac = Fraction(dx, circ.raio_mm)
        alfa_graus = graus_por_seno(sen_alfa_frac)
        cos_alfa = obter_cosseno_graus_racional(alfa_graus)
        sen_alfa = obter_seno_graus_racional(alfa_graus)

        # Peso da fatia Wi (em Newtons)
        # Volume aproximado = (largura_fatia / 1000) * (h_media / 1000) * 1m
        peso_fatia = (gamma * largura_fatia * h_media + 500_000) // 1_000_000
        peso_total_maciço += peso_fatia

        # Poropressão ui (Pa)
        ui = 0
        if projeto.nivel_dagua_y_mm is not None and y_base < projeto.nivel_dagua_y_mm:
            h_agua = min(y_topo, projeto.nivel_dagua_y_mm) - y_base
            ui = (9810 * h_agua) // 1000

        # Força atuante tangencial Ti = W * sen(alfa)
        t_i_frac = Fraction(peso_fatia, 1) * sen_alfa
        t_i_int = round(t_i_frac)

        # Comprimento da base da fatia l_i = b / cos(alfa) (em metros)
        if cos_alfa != 0:
            l_i_m_frac = Fraction(largura_fatia, 1000) / cos_alfa
        else:
            l_i_m_frac = Fraction(largura_fatia, 1000)

        # Força resistente Fellenius: S_i = c'*l_i + (W*cos(alfa) - u*l_i)*tan(phi)
        normal_fellenius = (Fraction(peso_fatia, 1) * cos_alfa) - (Fraction(ui, 1) * l_i_m_frac)
        if normal_fellenius < 0:
            normal_fellenius = Fraction(0, 1)

        res_fellenius_frac = (Fraction(c_solo, 1) * l_i_m_frac) + (normal_fellenius * tan_phi)
        res_fellenius_int = round(res_fellenius_frac)

        soma_atuante_num += t_i_int
        soma_resistente_fellenius_num += res_fellenius_int

        fatias.append(FatiaDiscretizada(
            indice=len(fatias) + 1,
            x_central_mm=x_m,
            largura_mm=largura_fatia,
            y_topo_mm=y_topo,
            y_base_mm=y_base,
            altura_media_mm=h_media,
            inclinacao_base_graus=alfa_graus,
            peso_fatia_n=peso_fatia,
            poropressao_base_pa=ui,
            forca_atuante_tangencial_n=t_i_int,
            forca_resistente_fellenius_n=res_fellenius_int,
        ))

    if soma_atuante_num <= 0:
        # Massa equilibrada ou ângulo plano
        fs_fellenius = Fraction(999, 100)
    else:
        fs_fellenius = Fraction(soma_resistente_fellenius_num, soma_atuante_num)

    # 2. Processo Iterativo de Bishop Simplificado
    fs_bishop = fs_fellenius if fs_fellenius > 0 else Fraction(1, 1)
    iteracoes = 0
    max_iter = 30

    denom_bishop_frac = Fraction(soma_atuante_num, 1)
    if denom_bishop_frac <= 0:
        fs_bishop = Fraction(999, 100)
    else:
        for _ in range(max_iter):
            iteracoes += 1
            numer_bishop_frac = Fraction(0, 1)
            for f in fatias:
                cos_a = obter_cosseno_graus_racional(f.inclinacao_base_graus)
                tan_a = obter_tangente_graus_racional(f.inclinacao_base_graus)
                b_m = Fraction(f.largura_mm, 1000)

                # m_alfa = cos(a) * (1 + (tan(a)*tan(phi))/FS)
                m_alfa = (cos_a * (Fraction(1, 1) + (tan_a * tan_phi / fs_bishop))).limit_denominator(1_000_000)
                if m_alfa <= Fraction(1, 10):
                    m_alfa = Fraction(1, 10)  # Evitar singularidades geométricas

                # Numerador individual da fatia
                termo_coesao = Fraction(c_solo, 1) * b_m
                termo_atrito = (Fraction(f.peso_fatia_n, 1) - Fraction(f.poropressao_base_pa, 1) * b_m) * tan_phi
                if termo_atrito < 0:
                    termo_atrito = Fraction(0, 1)

                numer_fatia = ((termo_coesao + termo_atrito) / m_alfa).limit_denominator(1_000_000)
                numer_bishop_frac += numer_fatia

            novo_fs = (numer_bishop_frac / denom_bishop_frac).limit_denominator(1_000_000)
            # Critério de convergência: diferença menor que 1/10000
            diff = abs(novo_fs - fs_bishop)
            fs_bishop = novo_fs
            if diff < Fraction(1, 10000):
                break

    norma_info = NIVEIS_SEGURANCA[projeto.nivel_seguranca_nbr11682]
    fs_min = norma_info.fs_minimo_fracao
    conforme = fs_bishop >= fs_min

    if fs_bishop < Fraction(1, 1):
        diagnostico = "INSTÁVEL (RUPTURA IMINENTE)"
    elif fs_bishop < fs_min:
        diagnostico = "MARGINAL (NÃO CONFORME COM A NBR 11682)"
    else:
        diagnostico = "ESTÁVEL (APROVADO PELA NBR 11682)"

    raio_m = Fraction(circ.raio_mm, 1000)
    momento_atuante = round(Fraction(soma_atuante_num, 1) * raio_m)
    momento_res_fel = round(Fraction(soma_resistente_fellenius_num, 1) * raio_m)
    momento_res_bish = round(fs_bishop * Fraction(momento_atuante, 1))

    return ResultadoEstabilidade(
        nome_talude=projeto.nome_talude,
        descricao=projeto.descricao,
        nivel_seguranca=projeto.nivel_seguranca_nbr11682,
        fs_minimo_exigido=fs_min,
        fator_seguranca_fellenius=fs_fellenius,
        fator_seguranca_bishop=fs_bishop,
        peso_total_maciço_n=peso_total_maciço,
        momento_atuante_total_nm=momento_atuante,
        momento_resistente_fellenius_nm=momento_res_fel,
        momento_resistente_bishop_nm=momento_res_bish,
        fatias=fatias,
        conforme_nbr11682=conforme,
        diagnostico=diagnostico,
        iteracoes_bishop=iteracoes,
    )
