"""Módulo de exportação de dados, relatórios e pacotes determinísticos (NBR 11682).

LOFRANO TECNOLOGIA.
Sanitização estrita contra injeção de fórmulas em CSV e empacotamento ZIP determinístico.
"""

import csv
import io
import os
from pathlib import Path
import stat
from typing import List, Sequence, Tuple
import zipfile

from .domain import (
    ResultadoEstabilidade,
    formatar_comprimento_m,
    formatar_forca_kn,
    formatar_fracao_decimal,
    formatar_pressao_kpa,
)
from .errors import ErroExportacao

# Caracteres perigosos para injeção de fórmulas em planilhas eletrônicas (CSV Injection)
CARACTERES_INJECAO_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def sanitizar_campo_csv(valor: str) -> str:
    """Higieniza campo CSV contra injeção de fórmulas e comandos maliciosos."""
    if not valor:
        return valor
    texto = str(valor)
    if texto.startswith(CARACTERES_INJECAO_FORMULA):
        return f"'{texto}"
    return texto


def gerar_fatias_csv_str(resultado: ResultadoEstabilidade) -> str:
    """Gera planilha CSV com o detalhamento físico e forças de cada fatia (lamela)."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")

    cabecalho = [
        "Fatia",
        "X_Central_m",
        "Largura_m",
        "Y_Topo_m",
        "Y_Base_m",
        "Altura_Media_m",
        "Inclinacao_Base_graus",
        "Peso_Fatia_kN",
        "Poropressao_Base_kPa",
        "Forca_Atuante_kN",
        "Forca_Resistente_Fellenius_kN",
    ]
    writer.writerow([sanitizar_campo_csv(c) for c in cabecalho])

    for f in resultado.fatias:
        linha = [
            str(f.indice),
            formatar_comprimento_m(f.x_central_mm),
            formatar_comprimento_m(f.largura_mm),
            formatar_comprimento_m(f.y_topo_mm),
            formatar_comprimento_m(f.y_base_mm),
            formatar_comprimento_m(f.altura_media_mm),
            str(f.inclinacao_base_graus),
            formatar_forca_kn(f.peso_fatia_n),
            formatar_pressao_kpa(f.poropressao_base_pa),
            formatar_forca_kn(f.forca_atuante_tangencial_n),
            formatar_forca_kn(f.forca_resistente_fellenius_n),
        ]
        writer.writerow([sanitizar_campo_csv(col) for col in linha])

    return output.getvalue()


def gerar_resumo_csv_str(resultado: ResultadoEstabilidade) -> str:
    """Gera planilha CSV com resumo dos fatores de segurança e esforços globais."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")

    cabecalho = [
        "Metodo_Calculo",
        "FS_Calculado",
        "FS_Minimo_NBR11682",
        "Nivel_Seguranca",
        "Status_Conformidade",
    ]
    writer.writerow([sanitizar_campo_csv(c) for c in cabecalho])

    status_fel = "APROVADO" if resultado.fator_seguranca_fellenius >= resultado.fs_minimo_exigido else "REPROVADO"
    status_bish = "APROVADO" if resultado.fator_seguranca_bishop >= resultado.fs_minimo_exigido else "REPROVADO"

    linhas = [
        ["Fellenius (Ordinário)", formatar_fracao_decimal(resultado.fator_seguranca_fellenius), formatar_fracao_decimal(resultado.fs_minimo_exigido), resultado.nivel_seguranca, status_fel],
        ["Bishop Simplificado", formatar_fracao_decimal(resultado.fator_seguranca_bishop), formatar_fracao_decimal(resultado.fs_minimo_exigido), resultado.nivel_seguranca, status_bish],
    ]

    for row in linhas:
        writer.writerow([sanitizar_campo_csv(col) for col in row])

    return output.getvalue()


def gerar_laudo_geotecnico_markdown(resultado: ResultadoEstabilidade) -> str:
    """Gera Laudo Técnico de Estabilidade Geotécnica em Markdown formal."""
    fs_fel_str = formatar_fracao_decimal(resultado.fator_seguranca_fellenius)
    fs_bish_str = formatar_fracao_decimal(resultado.fator_seguranca_bishop)
    fs_min_str = formatar_fracao_decimal(resultado.fs_minimo_exigido)

    status_geral = "ESTABILIDADE APROVADA" if resultado.conforme_nbr11682 else "RISCO DE RUPTURA / NÃO CONFORME"

    linhas = [
        "# Laudo Técnico de Estabilidade de Taludes e Encostas — NBR 11682",
        "",
        f"**Obra / Encosta:** {resultado.nome_talude}  ",
        f"**Descrição Geotécnica:** {resultado.descricao}  ",
        f"**Nível de Segurança Regulamentar:** {resultado.nivel_seguranca} (FS mín. exigido: {fs_min_str})  ",
        f"**Parecer Geotécnico Conclusivo:** **{status_geral}**  ",
        f"**Padrão de Engenharia:** LOFRANO TECNOLOGIA (Zero Float, Aritmética Racional Exata)  ",
        "",
        "---",
        "",
        "## 1. Fatores de Segurança Obtidos",
        "",
        "| Método de Análise | Fator de Segurança (FS) | Mínimo NBR 11682 | Diagnóstico Normativo |",
        "|---|---|---|---|",
        f"| **Bishop Simplificado** | **{fs_bish_str}** | {fs_min_str} | **{resultado.diagnostico}** |",
        f"| **Fellenius (Ordinário)** | **{fs_fel_str}** | {fs_min_str} | {'CONFORME' if resultado.fator_seguranca_fellenius >= resultado.fs_minimo_exigido else 'INSUFICIENTE'} |",
        "",
        f"> **Nota:** O método de Bishop Simplificado considera o equilíbrio de momentos com atuação de forças normais entre as lamelas, convergindo em {resultado.iteracoes_bishop} iterações.",
        "",
        "---",
        "",
        "## 2. Balanço de Forças e Momentos do Maciço Deslizante",
        "",
        f"- **Peso Total da Massa Escorregante:** {formatar_forca_kn(resultado.peso_total_maciço_n)}",
        f"- **Momento Instabilizante Atuante ($M_{{at}}$):** {resultado.momento_atuante_total_nm:,} N·m".replace(",", "."),
        f"- **Momento Estabilizante Resistente ($M_{{res}}$ - Bishop):** {resultado.momento_resistente_bishop_nm:,} N·m".replace(",", "."),
        f"- **Número de Fatias Verticais Analisadas:** {len(resultado.fatias)}",
        "",
        "---",
        "",
        "## 3. Detalhamento Lamela por Lamela (Discretização de Fatias)",
        "",
        "| Fatia | Posição X | Largura | Altura Média | Inclinação (α) | Peso (W) | Poropressão (u) | Atuante (T) | Resistente (S) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for f in resultado.fatias:
        linhas.append(
            f"| #{f.indice} | {formatar_comprimento_m(f.x_central_mm)} | {formatar_comprimento_m(f.largura_mm)} | "
            f"{formatar_comprimento_m(f.altura_media_mm)} | {f.inclinacao_base_graus}° | {formatar_forca_kn(f.peso_fatia_n)} | "
            f"{formatar_pressao_kpa(f.poropressao_base_pa)} | {formatar_forca_kn(f.forca_atuante_tangencial_n)} | "
            f"{formatar_forca_kn(f.forca_resistente_fellenius_n)} |"
        )

    linhas.extend([
        "",
        "---",
        "",
        "## 4. Conclusão e Diretrizes da ABNT NBR 11682:2009",
        "",
        "1. O talude foi analisado por equilíbrio limite bidimensional sob superfície de ruptura circular hipotética.",
        "2. A resistência ao cisalhamento do solo obedece à envoltória linear de Mohr-Coulomb ($s = c' + \\sigma' \\tan \\phi'$).",
        "3. Todos os cálculos matemáticos foram efetuados em frações racionais exatas (`Fraction`), garantindo ausência de erros de truncamento de ponto flutuante.",
        "",
        "---",
        "Engenharia Geotécnica e Software desenvolvidos por LOFRANO TECNOLOGIA.",
    ])

    return "\n".join(linhas) + "\n"


def criar_pacote_zip_deterministico(
    caminho_zip: Path,
    arquivos: Sequence[Tuple[str, bytes]],
) -> None:
    """Cria pacote ZIP determinístico com proteção contra sobrescrita via os.O_EXCL."""
    if caminho_zip.exists():
        raise ErroExportacao(
            f"O arquivo ZIP '{caminho_zip}' já existe e não será sobrescrito.",
            "ERR_ARQUIVO_EXISTENTE",
        )

    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY

    try:
        fd = os.open(str(caminho_zip), flags, 0o644)
    except OSError as e:
        raise ErroExportacao(f"Falha ao abrir descritor exclusivo de arquivo ZIP: {e}", "ERR_ARQUIVO_ZIP")

    data_fixa = (2026, 1, 1, 0, 0, 0)

    try:
        with os.fdopen(fd, "wb") as f_out:
            with zipfile.ZipFile(f_out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for nome_arquivo, conteudo_bytes in sorted(arquivos, key=lambda x: x[0]):
                    zinfo = zipfile.ZipInfo(filename=nome_arquivo, date_time=data_fixa)
                    zinfo.compress_type = zipfile.ZIP_DEFLATED
                    zinfo.external_attr = (stat.S_IFREG | 0o644) << 16
                    zf.writestr(zinfo, conteudo_bytes)
    except Exception as e:
        if caminho_zip.exists():
            caminho_zip.unlink(missing_ok=True)
        raise ErroExportacao(f"Falha ao gravar arquivo ZIP determinístico: {e}", "ERR_GRAVACAO_ZIP")
