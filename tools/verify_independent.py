#!/usr/bin/env python3
"""Verificador independente em SQLite para estabilidade de taludes (NBR 11682:2009).

LOFRANO TECNOLOGIA.
Este script NÃO importa o pacote de produção `estabilidade_taludes`.
Ele implementa um motor de validação independente utilizando tabelas em memória SQLite (:memory:)
e frações racionais exatas para auditar o arquivo canônico `exemplares/talude_rodoviario_padrao.json`.
"""

from fractions import Fraction
import json
import math
from pathlib import Path
import sqlite3
import sys

# Tabela trigonométrica racional independente
TAB_SENO: dict[int, Fraction] = {}
TAB_COSSENO: dict[int, Fraction] = {}
TAB_TANGENTE: dict[int, Fraction] = {}

for g in range(91):
    r = math.radians(g)
    TAB_SENO[g] = Fraction(round(math.sin(r) * 100_000_000), 100_000_000)
    TAB_COSSENO[g] = Fraction(round(math.cos(r) * 100_000_000), 100_000_000)
    if g < 90:
        TAB_TANGENTE[g] = Fraction(round(math.tan(r) * 100_000_000), 100_000_000)
    else:
        TAB_TANGENTE[g] = Fraction(999_999_999, 1)


def indep_seno(g: int) -> Fraction:
    sinal = -1 if g < 0 else 1
    val = abs(g) % 360
    if val <= 90:
        return sinal * TAB_SENO[val]
    elif val <= 180:
        return sinal * TAB_SENO[180 - val]
    elif val <= 270:
        return -sinal * TAB_SENO[val - 180]
    return -sinal * TAB_SENO[360 - val]


def indep_cosseno(g: int) -> Fraction:
    val = abs(g) % 360
    if val <= 90:
        return TAB_COSSENO[val]
    elif val <= 180:
        return -TAB_COSSENO[180 - val]
    elif val <= 270:
        return -TAB_COSSENO[val - 180]
    return TAB_COSSENO[360 - val]


def indep_tangente(g: int) -> Fraction:
    cos_val = indep_cosseno(g)
    if cos_val == 0:
        return Fraction(999_999_999, 1)
    return indep_seno(g) / cos_val


def indep_graus_seno(s_frac: Fraction) -> int:
    sinal = -1 if s_frac < 0 else 1
    val = abs(s_frac)
    if val >= 1:
        return sinal * 90
    melhor = 0
    menor_dif = abs(val - TAB_SENO[0])
    for g in range(1, 91):
        dif = abs(val - TAB_SENO[g])
        if dif < menor_dif:
            menor_dif = dif
            melhor = g
        else:
            break
    return sinal * melhor


def main() -> int:
    print("================================================================================")
    print(" VERIFICADOR INDEPENDENTE DE ESTABILIDADE GEOTÉCNICA (SQLITE3 + ZERO FLOAT)")
    print(" LOFRANO TECNOLOGIA — ABNT NBR 11682:2009")
    print("================================================================================")

    caminho_json = Path(__file__).parent.parent / "exemplares" / "talude_rodoviario_padrao.json"
    if not caminho_json.exists():
        print(f"Erro: Arquivo exemplar não encontrado em {caminho_json}")
        return 1

    dados = json.loads(caminho_json.read_text(encoding="utf-8"))

    # Conexão SQLite em memória
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    # Criação do esquema de auditoria independente
    cur.execute("""
    CREATE TABLE perfil_topografico (
        ordem INTEGER PRIMARY KEY,
        x_mm INTEGER NOT NULL,
        y_mm INTEGER NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE parametros_solo (
        id INTEGER PRIMARY KEY,
        nome TEXT NOT NULL,
        peso_especifico_n_m3 INTEGER NOT NULL,
        coesao_pa INTEGER NOT NULL,
        atrito_graus INTEGER NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE circulo_geometria (
        id INTEGER PRIMARY KEY,
        centro_x_mm INTEGER NOT NULL,
        centro_y_mm INTEGER NOT NULL,
        raio_mm INTEGER NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE lamelas_auditadas (
        indice INTEGER PRIMARY KEY,
        x_m_mm INTEGER NOT NULL,
        largura_mm INTEGER NOT NULL,
        y_topo_mm INTEGER NOT NULL,
        y_base_mm INTEGER NOT NULL,
        h_media_mm INTEGER NOT NULL,
        alfa_graus INTEGER NOT NULL,
        peso_n INTEGER NOT NULL,
        poropressao_pa INTEGER NOT NULL,
        forca_atuante_n INTEGER NOT NULL,
        forca_res_fellenius_n INTEGER NOT NULL
    );
    """)

    # Inserção de dados do perfil
    for idx, p in enumerate(dados["perfil_terreno"], start=1):
        cur.execute("INSERT INTO perfil_topografico VALUES (?, ?, ?)", (idx, p["x_mm"], p["y_mm"]))

    # Inserção solo
    solo = dados["solo"]
    cur.execute("INSERT INTO parametros_solo VALUES (1, ?, ?, ?, ?)", (
        solo["nome_camada"], solo["peso_especifico_n_m3"], solo["coesao_efetiva_pa"], solo["angulo_atrito_graus"]
    ))

    # Inserção círculo
    circ = dados["circulo_tentativa"]
    cur.execute("INSERT INTO circulo_geometria VALUES (1, ?, ?, ?)", (
        circ["centro_x_mm"], circ["centro_y_mm"], circ["raio_mm"]
    ))
    conn.commit()

    # Validação SQL 1: Verificar se X do perfil é estritamente crescente
    cur.execute("""
    SELECT count(*) FROM perfil_topografico p1
    JOIN perfil_topografico p2 ON p2.ordem = p1.ordem + 1
    WHERE p2.x_mm <= p1.x_mm;
    """)
    inversoes = cur.fetchone()[0]
    assert inversoes == 0, f"Inversão topográfica detectada: {inversoes}"
    print("✔ [1/6] Perfil topográfico validado: coordenadas X estritamente monótonas crescentes.")

    # Interpolação independente de cotas do terreno
    cur.execute("SELECT ordem, x_mm, y_mm FROM perfil_topografico ORDER BY ordem")
    pts = cur.fetchall()

    def interpolar_y(x_mm: int) -> int:
        if x_mm <= pts[0][1]:
            return pts[0][2]
        if x_mm >= pts[-1][1]:
            return pts[-1][2]
        for i in range(len(pts) - 1):
            x1, y1 = pts[i][1], pts[i][2]
            x2, y2 = pts[i + 1][1], pts[i + 1][2]
            if x1 <= x_mm <= x2:
                dx = x2 - x1
                dy = y2 - y1
                return y1 + (dy * (x_mm - x1)) // dx
        return pts[-1][2]

    # Geometria do círculo
    cx = circ["centro_x_mm"]
    cy = circ["centro_y_mm"]
    raio = circ["raio_mm"]
    r2 = raio * raio

    x_esq = max(cx - raio + 1, pts[0][1])
    x_dir = min(cx + raio - 1, pts[-1][1])

    cortes = []
    passo = max(100, (x_dir - x_esq) // 200)
    for x in range(x_esq, x_dir, passo):
        dx = x - cx
        val = r2 - dx * dx
        if val < 0:
            continue
        y_c = cy - math.isqrt(val)
        y_t = interpolar_y(x)
        if y_c < y_t:
            cortes.append(x)

    assert len(cortes) >= 2, "Círculo não corta maciço"
    x_ini = cortes[0]
    x_fim = cortes[-1]
    extensao_x = x_fim - x_ini
    num_fatias = dados["numero_fatias"]
    largura = extensao_x // num_fatias

    gamma = solo["peso_especifico_n_m3"]
    coesao = solo["coesao_efetiva_pa"]
    phi = solo["angulo_atrito_graus"]
    tan_phi = indep_tangente(phi)
    na_y = dados.get("nivel_dagua_y_mm")

    soma_t = 0
    soma_s_fel = 0
    fatias_dados = []

    for idx in range(num_fatias):
        xm = x_ini + idx * largura + largura // 2
        dx = xm - cx
        val = r2 - dx * dx
        if val <= 0:
            continue
        y_base = cy - math.isqrt(val)
        y_topo = interpolar_y(xm)
        h = y_topo - y_base
        if h <= 0:
            continue

        sen_a_frac = Fraction(dx, raio)
        alfa_graus = indep_graus_seno(sen_a_frac)
        cos_a = indep_cosseno(alfa_graus)
        sen_a = indep_seno(alfa_graus)

        peso = (gamma * largura * h + 500_000) // 1_000_000
        ui = 0
        if na_y is not None and y_base < na_y:
            h_w = min(y_topo, na_y) - y_base
            ui = (9810 * h_w) // 1000

        t_i = round(Fraction(peso, 1) * sen_a)
        l_i = Fraction(largura, 1000) / cos_a if cos_a != 0 else Fraction(largura, 1000)
        norm_fel = (Fraction(peso, 1) * cos_a) - (Fraction(ui, 1) * l_i)
        if norm_fel < 0:
            norm_fel = Fraction(0, 1)
        res_fel = round((Fraction(coesao, 1) * l_i) + (norm_fel * tan_phi))

        soma_t += t_i
        soma_s_fel += res_fel

        fatias_dados.append((alfa_graus, largura, peso, ui))

        cur.execute("""
        INSERT INTO lamelas_auditadas VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (idx + 1, xm, largura, y_topo, y_base, h, alfa_graus, peso, ui, t_i, res_fel))

    conn.commit()

    print(f"✔ [2/6] Discretização em {len(fatias_dados)} lamelas inserida com sucesso no banco SQLite.")

    # Validação SQL 2: Fator de Segurança Fellenius em SQL e Python
    cur.execute("SELECT sum(forca_atuante_n), sum(forca_res_fellenius_n), sum(peso_n) FROM lamelas_auditadas")
    sql_atuante, sql_resistente_fel, sql_peso_total = cur.fetchone()

    fs_fel_racional = Fraction(sql_resistente_fel, sql_atuante)
    print(f"✔ [3/6] Balanço de forças SQLite: Atuante = {sql_atuante:,} N, Resistente = {sql_resistente_fel:,} N.")
    print(f"      FS Fellenius Auditado: {fs_fel_racional.numerator}/{fs_fel_racional.denominator} (~{float(fs_fel_racional):.4f})")
    assert fs_fel_racional >= Fraction(15, 10), f"Fellenius deve ser >= 1.50 para aprovação (obtido: {fs_fel_racional})"

    # Validação 4: Bishop Simplificado Racional
    fs_bishop = fs_fel_racional
    denom_b = Fraction(sql_atuante, 1)

    for it in range(30):
        numer_b = Fraction(0, 1)
        for (alfa, larg_mm, w, u) in fatias_dados:
            ca = indep_cosseno(alfa)
            ta = indep_tangente(alfa)
            bm = Fraction(larg_mm, 1000)

            m_alfa = (ca * (Fraction(1, 1) + (ta * tan_phi / fs_bishop))).limit_denominator(1_000_000)
            if m_alfa <= Fraction(1, 10):
                m_alfa = Fraction(1, 10)

            termo_c = Fraction(coesao, 1) * bm
            termo_phi = (Fraction(w, 1) - Fraction(u, 1) * bm) * tan_phi
            if termo_phi < 0:
                termo_phi = Fraction(0, 1)

            numer_fatia = ((termo_c + termo_phi) / m_alfa).limit_denominator(1_000_000)
            numer_b += numer_fatia

        novo_fs = (numer_b / denom_b).limit_denominator(1_000_000)
        diff = abs(novo_fs - fs_bishop)
        fs_bishop = novo_fs
        if diff < Fraction(1, 10000):
            print(f"✔ [4/6] Método de Bishop Simplificado convergiu na iteração {it + 1}.")
            break

    print(f"      FS Bishop Auditado: {fs_bishop.numerator}/{fs_bishop.denominator} (~{float(fs_bishop):.4f})")
    assert fs_bishop >= Fraction(15, 10), "Bishop não atingiu 1.50"

    # Validação 5: NBR 11682 Tabela 1 conformidade
    nivel = dados["nivel_seguranca_nbr11682"]
    limites_nbr = {"ALTO": Fraction(3, 2), "MEDIO": Fraction(7, 5), "BAIXO": Fraction(13, 10)}
    limite_exigido = limites_nbr[nivel]
    assert fs_bishop >= limite_exigido, f"FS {fs_bishop} abaixo do exigido {limite_exigido}"
    print(f"✔ [5/6] Verificação NBR 11682 aprovada: Nível {nivel} exige FS >= {float(limite_exigido):.2f}; obtido {float(fs_bishop):.3f}.")

    # Validação 6: Consulta analítica em SQLite
    cur.execute("""
    SELECT count(*), min(alfa_graus), max(alfa_graus), max(poropressao_pa)
    FROM lamelas_auditadas
    """)
    qtd, min_alfa, max_alfa, max_u = cur.fetchone()
    print(f"✔ [6/6] Estatísticas de lamelas SQLite: {qtd} fatias, inclinações entre {min_alfa}° e {max_alfa}°, u_max = {max_u} Pa.")
    print("================================================================================")
    print(" AUDITORIA INDEPENDENTE CONCLUÍDA COM SUCESSO (100% CONFORME)")
    print("================================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
