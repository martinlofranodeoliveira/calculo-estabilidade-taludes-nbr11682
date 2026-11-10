"""Gerador de relatório visual em SVG de alta resolução (1440x900).

LOFRANO TECNOLOGIA.
Visualização do perfil do talude, círculo de deslizamento, lamelas discretizadas,
lençol freático e painéis de conformidade com a ABNT NBR 11682:2009.
"""

from fractions import Fraction
from typing import List, Tuple

from .domain import (
    ResultadoEstabilidade,
    TaludeInput,
    formatar_comprimento_m,
    formatar_forca_kn,
    formatar_fracao_decimal,
    formatar_pressao_kpa,
)


def gerar_svg_estabilidade(projeto: TaludeInput, resultado: ResultadoEstabilidade) -> str:
    """Gera painel técnico em SVG (1440x900) ilustrando o talude e o cálculo NBR 11682."""
    largura_total = 1440
    altura_total = 900

    # Coordenadas extremas para enquadramento do desenho
    xs = [p.x_mm for p in projeto.perfil_terreno]
    ys = [p.y_mm for p in projeto.perfil_terreno]

    circ = projeto.circulo_tentativa
    xs.extend([circ.centro_x_mm - circ.raio_mm, circ.centro_x_mm + circ.raio_mm])
    ys.extend([circ.centro_y_mm - circ.raio_mm, circ.centro_y_mm])

    x_min = min(xs)
    x_max = max(xs)
    y_min = min(ys)
    y_max = max(ys)

    # Margem geométrica
    delta_x = max(1000, x_max - x_min)
    delta_y = max(1000, y_max - y_min)
    margem_x = delta_x // 10
    margem_y = delta_y // 10

    gx_min = x_min - margem_x
    gx_max = x_max + margem_x
    gy_min = y_min - margem_y
    gy_max = y_max + margem_y

    span_x = max(1, gx_max - gx_min)
    span_y = max(1, gy_max - gy_min)

    # Área reservada para o perfil geométrico (x: 50 a 880, y: 160 a 760)
    vp_x0 = 50
    vp_y0 = 170
    vp_larg = 830
    vp_alt = 580

    def mapear_x(x_mm: int) -> int:
        return vp_x0 + ((x_mm - gx_min) * vp_larg) // span_x

    def mapear_y(y_mm: int) -> int:
        # SVG inverte Y (origem no topo)
        return vp_y0 + vp_alt - ((y_mm - gy_min) * vp_alt) // span_y

    # Caminho do terreno
    pontos_svg = []
    for p in projeto.perfil_terreno:
        px = mapear_x(p.x_mm)
        py = mapear_y(p.y_mm)
        pontos_svg.append(f"{px},{py}")
    linha_terreno = " ".join(pontos_svg)

    # Polígono preenchido do maciço terroso
    p_inicio = projeto.perfil_terreno[0]
    p_fim = projeto.perfil_terreno[-1]
    px_ini = mapear_x(p_inicio.x_mm)
    py_base = vp_y0 + vp_alt
    px_fim = mapear_x(p_fim.x_mm)

    poligono_terreno = f"{px_ini},{py_base} " + linha_terreno + f" {px_fim},{py_base}"

    # Fatias (Lamelas)
    fatias_svg = []
    for f in resultado.fatias:
        x_esq = f.x_central_mm - f.largura_mm // 2
        x_dir = f.x_central_mm + f.largura_mm // 2
        svg_x1 = mapear_x(x_esq)
        svg_x2 = mapear_x(x_dir)
        svg_y_topo = mapear_y(f.y_topo_mm)
        svg_y_base = mapear_y(f.y_base_mm)

        fatia_path = (
            f"M {svg_x1} {svg_y_topo} "
            f"L {svg_x2} {svg_y_topo} "
            f"L {svg_x2} {svg_y_base} "
            f"L {svg_x1} {svg_y_base} Z"
        )
        fatias_svg.append(fatia_path)

    # Coordenadas do centro e círculo
    cx_svg = mapear_x(circ.centro_x_mm)
    cy_svg = mapear_y(circ.centro_y_mm)
    # Raio em pixels
    raio_px = (circ.raio_mm * vp_larg) // span_x

    # Cores de diagnóstico
    if resultado.conforme_nbr11682:
        cor_status = "#10b981"  # Verde esmeralda
        texto_status = "CONFORME NBR 11682"
        badge_bg = "rgba(16, 185, 129, 0.18)"
    else:
        cor_status = "#ef4444"  # Vermelho
        texto_status = "NÃO CONFORME / ALERTA"
        badge_bg = "rgba(239, 68, 68, 0.18)"

    fs_bish_str = formatar_fracao_decimal(resultado.fator_seguranca_bishop)
    fs_fel_str = formatar_fracao_decimal(resultado.fator_seguranca_fellenius)
    fs_min_str = formatar_fracao_decimal(resultado.fs_minimo_exigido)

    # Nível d'água se existente
    svg_na = ""
    if projeto.nivel_dagua_y_mm is not None:
        y_na_svg = mapear_y(projeto.nivel_dagua_y_mm)
        svg_na = f"""
        <!-- Nível Freático -->
        <line x1="{vp_x0}" y1="{y_na_svg}" x2="{vp_x0 + vp_larg}" y2="{y_na_svg}"
              stroke="#38bdf8" stroke-width="2" stroke-dasharray="6,4" />
        <text x="{vp_x0 + 10}" y="{y_na_svg - 8}" fill="#38bdf8" font-size="12" font-weight="600" font-family="sans-serif">
            Nível Freático (N.A. = {formatar_comprimento_m(projeto.nivel_dagua_y_mm)})
        </text>
        """

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura_total} {altura_total}" width="{largura_total}" height="{altura_total}">
    <defs>
        <linearGradient id="bg-grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#090d16" />
            <stop offset="100%" stop-color="#0f172a" />
        </linearGradient>
        <linearGradient id="card-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#1e293b" />
            <stop offset="100%" stop-color="#111827" />
        </linearGradient>
        <linearGradient id="solo-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#334155" stop-opacity="0.8" />
            <stop offset="100%" stop-color="#1e293b" stop-opacity="0.9" />
        </linearGradient>
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" stroke-width="1" stroke-opacity="0.5"/>
        </pattern>
        <clipPath id="viewport-clip">
            <rect x="{vp_x0}" y="{vp_y0}" width="{vp_larg}" height="{vp_alt}" rx="8" />
        </clipPath>
    </defs>

    <!-- Fundo Principal -->
    <rect width="{largura_total}" height="{altura_total}" fill="url(#bg-grad)" />
    <rect width="{largura_total}" height="{altura_total}" fill="url(#grid)" />

    <!-- Barra de Título Superior -->
    <rect x="30" y="24" width="1380" height="110" rx="12" fill="url(#card-grad)" stroke="#334155" stroke-width="1" />

    <text x="56" y="60" fill="#94a3b8" font-size="13" font-weight="700" letter-spacing="1.5" font-family="sans-serif">
        LOFRANO TECNOLOGIA • ENGENHARIA GEOTÉCNICA COMPUTACIONAL DETERMINÍSTICA
    </text>
    <text x="56" y="96" fill="#f8fafc" font-size="26" font-weight="800" font-family="sans-serif">
        {projeto.nome_talude} — Estabilidade de Taludes e Encostas (NBR 11682)
    </text>

    <!-- Badges Superiores de Status -->
    <rect x="1080" y="44" width="300" height="68" rx="8" fill="{badge_bg}" stroke="{cor_status}" stroke-width="1.5" />
    <text x="1100" y="70" fill="{cor_status}" font-size="12" font-weight="700" letter-spacing="1" font-family="sans-serif">
        SITUAÇÃO REGULAMENTAR
    </text>
    <text x="1100" y="96" fill="#f8fafc" font-size="18" font-weight="800" font-family="sans-serif">
        {texto_status}
    </text>

    <!-- Painel do Desenho Topográfico Geotécnico -->
    <rect x="30" y="150" width="870" height="620" rx="12" fill="url(#card-grad)" stroke="#334155" stroke-width="1" />
    <text x="50" y="180" fill="#38bdf8" font-size="14" font-weight="700" letter-spacing="0.5" font-family="sans-serif">
        SEÇÃO TRANSVERSAL E SUPERFÍCIE DE RUPTURA HIPOTÉTICA
    </text>

    <g clip-path="url(#viewport-clip)">
        <!-- Maciço Terroso (Sólido) -->
        <polygon points="{poligono_terreno}" fill="url(#solo-grad)" />

        <!-- Lamelas / Fatias Discretizadas -->
        {"".join(f'<path d="{f_path}" fill="#0284c7" fill-opacity="0.22" stroke="#38bdf8" stroke-width="1" stroke-dasharray="2,2"/>' for f_path in fatias_svg)}

        <!-- Superfície do Terreno (Linha Topográfica) -->
        <polyline points="{linha_terreno}" fill="none" stroke="#22c55e" stroke-width="3.5" stroke-linejoin="round" />

        <!-- Círculo de Ruptura Geotécnico -->
        <circle cx="{cx_svg}" cy="{cy_svg}" r="{raio_px}" fill="none" stroke="#f43f5e" stroke-width="2.5" stroke-dasharray="8,4" />

        <!-- Centro de Rotação O(X, Y) -->
        <circle cx="{cx_svg}" cy="{cy_svg}" r="5" fill="#f43f5e" />
        <line x1="{cx_svg - 10}" y1="{cy_svg}" x2="{cx_svg + 10}" y2="{cy_svg}" stroke="#f43f5e" stroke-width="2" />
        <line x1="{cx_svg}" y1="{cy_svg - 10}" x2="{cx_svg}" y2="{cy_svg + 10}" stroke="#f43f5e" stroke-width="2" />
        <text x="{cx_svg + 12}" y="{cy_svg + 5}" fill="#fda4af" font-size="12" font-weight="600" font-family="sans-serif">
            Centro O ({formatar_comprimento_m(circ.centro_x_mm)}, {formatar_comprimento_m(circ.centro_y_mm)})
        </text>

        {svg_na}
    </g>

    <!-- Legenda no Rodapé do Gráfico -->
    <g transform="translate(50, 742)">
        <line x1="0" y1="0" x2="25" y2="0" stroke="#22c55e" stroke-width="3" />
        <text x="32" y="4" fill="#94a3b8" font-size="11" font-family="sans-serif">Perfil Terreno</text>

        <line x1="130" y1="0" x2="155" y2="0" stroke="#f43f5e" stroke-width="2" stroke-dasharray="4,2" />
        <text x="162" y="4" fill="#94a3b8" font-size="11" font-family="sans-serif">Superfície Ruptura</text>

        <rect x="290" y="-8" width="16" height="16" fill="#0284c7" fill-opacity="0.3" stroke="#38bdf8" stroke-width="1" />
        <text x="314" y="4" fill="#94a3b8" font-size="11" font-family="sans-serif">Lamelas ({len(resultado.fatias)})</text>
    </g>

    <!-- Painel Lateral Direito: Resultados e Coeficientes -->
    <!-- Card 1: Fatores de Segurança -->
    <rect x="920" y="150" width="490" height="240" rx="12" fill="url(#card-grad)" stroke="#334155" stroke-width="1" />
    <text x="944" y="184" fill="#38bdf8" font-size="15" font-weight="700" letter-spacing="0.5" font-family="sans-serif">
        FATORES DE SEGURANÇA (FS)
    </text>

    <!-- Bishop -->
    <rect x="944" y="204" width="215" height="100" rx="8" fill="#0f172a" stroke="{cor_status}" stroke-width="1.5" />
    <text x="960" y="228" fill="#94a3b8" font-size="11" font-weight="600" font-family="sans-serif">BISHOP SIMPLIFICADO</text>
    <text x="960" y="268" fill="#f8fafc" font-size="32" font-weight="800" font-family="sans-serif">{fs_bish_str}</text>
    <text x="960" y="292" fill="{cor_status}" font-size="11" font-weight="700" font-family="sans-serif">Iterações: {resultado.iteracoes_bishop}</text>

    <!-- Fellenius -->
    <rect x="1175" y="204" width="215" height="100" rx="8" fill="#0f172a" stroke="#475569" stroke-width="1" />
    <text x="1191" y="228" fill="#94a3b8" font-size="11" font-weight="600" font-family="sans-serif">FELLENIUS ORDINÁRIO</text>
    <text x="1191" y="268" fill="#cbd5e1" font-size="32" font-weight="800" font-family="sans-serif">{fs_fel_str}</text>
    <text x="1191" y="292" fill="#94a3b8" font-size="11" font-weight="600" font-family="sans-serif">Método Suéco</text>

    <text x="944" y="336" fill="#94a3b8" font-size="12" font-family="sans-serif">
        Nível de Segurança: <tspan fill="#f8fafc" font-weight="700">{resultado.nivel_seguranca}</tspan> | FS Mínimo NBR 11682: <tspan fill="#f8fafc" font-weight="700">{fs_min_str}</tspan>
    </text>
    <text x="944" y="360" fill="{cor_status}" font-size="13" font-weight="700" font-family="sans-serif">
        {resultado.diagnostico}
    </text>

    <!-- Card 2: Balanço de Forças e Momentos -->
    <rect x="920" y="410" width="490" height="190" rx="12" fill="url(#card-grad)" stroke="#334155" stroke-width="1" />
    <text x="944" y="442" fill="#38bdf8" font-size="15" font-weight="700" letter-spacing="0.5" font-family="sans-serif">
        BALANÇO DE ESFORÇOS DO MACIÇO
    </text>

    <g transform="translate(944, 465)">
        <text x="0" y="15" fill="#94a3b8" font-size="13" font-family="sans-serif">Peso Total da Massa Deslizante:</text>
        <text x="440" y="15" fill="#f8fafc" font-size="13" font-weight="700" text-anchor="end" font-family="sans-serif">{formatar_forca_kn(resultado.peso_total_maciço_n)}</text>

        <text x="0" y="45" fill="#94a3b8" font-size="13" font-family="sans-serif">Momento Atuante Desestabilizador (Mat):</text>
        <text x="440" y="45" fill="#f43f5e" font-size="13" font-weight="700" text-anchor="end" font-family="sans-serif">{resultado.momento_atuante_total_nm:,} N·m</text>

        <text x="0" y="75" fill="#94a3b8" font-size="13" font-family="sans-serif">Momento Resistente (Mres - Bishop):</text>
        <text x="440" y="75" fill="#10b981" font-size="13" font-weight="700" text-anchor="end" font-family="sans-serif">{resultado.momento_resistente_bishop_nm:,} N·m</text>

        <text x="0" y="105" fill="#94a3b8" font-size="13" font-family="sans-serif">Momento Resistente (Mres - Fellenius):</text>
        <text x="440" y="105" fill="#38bdf8" font-size="13" font-weight="700" text-anchor="end" font-family="sans-serif">{resultado.momento_resistente_fellenius_nm:,} N·m</text>
    </g>

    <!-- Card 3: Parâmetros Geotécnicos do Solo -->
    <rect x="920" y="620" width="490" height="150" rx="12" fill="url(#card-grad)" stroke="#334155" stroke-width="1" />
    <text x="944" y="652" fill="#38bdf8" font-size="15" font-weight="700" letter-spacing="0.5" font-family="sans-serif">
        PARÂMETROS GEOTÉCNICOS (MOHR-COULOMB)
    </text>

    <g transform="translate(944, 675)">
        <text x="0" y="15" fill="#94a3b8" font-size="13" font-family="sans-serif">Solo / Formação:</text>
        <text x="440" y="15" fill="#f8fafc" font-size="13" font-weight="700" text-anchor="end" font-family="sans-serif">{projeto.solo.nome_camada}</text>

        <text x="0" y="42" fill="#94a3b8" font-size="13" font-family="sans-serif">Coesão Efetiva (c'):</text>
        <text x="440" y="42" fill="#f8fafc" font-size="13" font-weight="700" text-anchor="end" font-family="sans-serif">{formatar_pressao_kpa(projeto.solo.coesao_efetiva_pa)}</text>

        <text x="0" y="69" fill="#94a3b8" font-size="13" font-family="sans-serif">Ângulo de Atrito Interno (φ'):</text>
        <text x="440" y="69" fill="#f8fafc" font-size="13" font-weight="700" text-anchor="end" font-family="sans-serif">{projeto.solo.angulo_atrito_graus}°</text>

        <text x="0" y="96" fill="#94a3b8" font-size="13" font-family="sans-serif">Peso Específico Natural (γ):</text>
        <text x="440" y="96" fill="#f8fafc" font-size="13" font-weight="700" text-anchor="end" font-family="sans-serif">{projeto.solo.peso_especifico_n_m3 // 1000} kN/m³</text>
    </g>

    <!-- Barra de Rodapé -->
    <rect x="30" y="790" width="1380" height="80" rx="10" fill="url(#card-grad)" stroke="#334155" stroke-width="1" />
    <text x="56" y="826" fill="#f8fafc" font-size="13" font-weight="700" font-family="sans-serif">
        CONFORMIDADE TOTAL ABNT NBR 11682:2009 — ESTABILIDADE DE ENCOSTAS
    </text>
    <text x="56" y="848" fill="#94a3b8" font-size="11" font-family="sans-serif">
        Cálculo determinístico em frações racionais exatas (Zero Float). Fellenius &amp; Bishop Simplificado. LOFRANO TECNOLOGIA.
    </text>
    <text x="1380" y="836" fill="#64748b" font-size="12" text-anchor="end" font-family="sans-serif">
        Raio: {formatar_comprimento_m(circ.raio_mm)} | Fatias: {len(resultado.fatias)} | Resolução: 1440x900
    </text>
</svg>
"""
    return svg
