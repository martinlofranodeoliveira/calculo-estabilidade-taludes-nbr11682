"""Interface de Linha de Comando (CLI) para Estabilidade de Taludes NBR 11682.

LOFRANO TECNOLOGIA.
Todos os comandos e saídas em português brasileiro (pt-BR).
"""

import argparse
from pathlib import Path
import sys
from typing import List, Optional

from . import __version__
from .calculator import calcular_estabilidade_talude
from .codecs import codificar_resultado_json_str, decodificar_talude_json_str
from .domain import (
    CirculoRuptura,
    Ponto2D,
    PropriedadesSolo,
    TaludeInput,
    formatar_comprimento_m,
    formatar_forca_kn,
    formatar_fracao_decimal,
    formatar_pressao_kpa,
)
from .errors import ErroEstabilidadeTalude
from .exports import (
    criar_pacote_zip_deterministico,
    gerar_fatias_csv_str,
    gerar_laudo_geotecnico_markdown,
    gerar_resumo_csv_str,
)
from .svg_report import gerar_svg_estabilidade
from .tabelas_nbr11682 import NIVEIS_SEGURANCA, SOLOS_REFERENCIA


def gerar_exemplo_talude() -> TaludeInput:
    """Gera um talude de corte rodoviário padrão com dados representativos."""
    return TaludeInput(
        nome_talude="Talude de Corte Rodoviário - Estaca 142+00",
        descricao="Corte em encosta natural de solo residual com berma intermediária e lençol freático rebaixado.",
        nivel_seguranca_nbr11682="ALTO",
        perfil_terreno=[
            Ponto2D(x_mm=0, y_mm=10000),         # Pé do talude (0,0 m, cota 10,0 m)
            Ponto2D(x_mm=15000, y_mm=10000),     # Pista / acostamento (15,0 m, cota 10,0 m)
            Ponto2D(x_mm=30000, y_mm=20000),     # 1ª rampa 1:1,5 (30,0 m, cota 20,0 m)
            Ponto2D(x_mm=34000, y_mm=20000),     # Berma de equilíbrio (34,0 m, cota 20,0 m)
            Ponto2D(x_mm=49000, y_mm=30000),     # 2ª rampa (49,0 m, cota 30,0 m)
            Ponto2D(x_mm=65000, y_mm=31000),     # Crista natural (65,0 m, cota 31,0 m)
        ],
        circulo_tentativa=CirculoRuptura(
            centro_x_mm=28000,
            centro_y_mm=42000,
            raio_mm=33000,
        ),
        solo=PropriedadesSolo(
            nome_camada="Solo residual de gnaisse (argila siltosa)",
            peso_especifico_n_m3=18500,          # 18,5 kN/m³
            coesao_efetiva_pa=22000,             # 22,0 kPa
            angulo_atrito_graus=26,              # 26°
        ),
        numero_fatias=16,
        nivel_dagua_y_mm=12000,                  # N.A. em 12,0 m
        sobrecarga_crista_pa=0,
    )


def comando_calcular(args: argparse.Namespace) -> int:
    """Executa a rotina de análise de estabilidade e emissão de laudos."""
    caminho_entrada = Path(args.arquivo_json)
    if not caminho_entrada.exists():
        sys.stderr.write(f"Erro: Arquivo de entrada não encontrado: {caminho_entrada}\n")
        return 2

    try:
        conteudo_json = caminho_entrada.read_text(encoding="utf-8")
        projeto = decodificar_talude_json_str(conteudo_json)
        resultado = calcular_estabilidade_talude(projeto)
    except ErroEstabilidadeTalude as err:
        sys.stderr.write(f"Erro de Validação Geotécnica [{err.codigo}]: {err.mensagem}\n")
        return 1
    except Exception as err:
        sys.stderr.write(f"Erro inesperado no processamento: {err}\n")
        return 2

    # Saídas em arquivos se solicitadas
    if args.saida_json:
        p_json = Path(args.saida_json)
        p_json.write_text(codificar_resultado_json_str(resultado), encoding="utf-8")

    if args.saida_csv_resumo:
        p_csv_res = Path(args.saida_csv_resumo)
        p_csv_res.write_text(gerar_resumo_csv_str(resultado), encoding="utf-8")

    if args.saida_csv_fatias:
        p_csv_fat = Path(args.saida_csv_fatias)
        p_csv_fat.write_text(gerar_fatias_csv_str(resultado), encoding="utf-8")

    if args.saida_md:
        p_md = Path(args.saida_md)
        p_md.write_text(gerar_laudo_geotecnico_markdown(resultado), encoding="utf-8")

    if args.saida_svg:
        p_svg = Path(args.saida_svg)
        p_svg.write_text(gerar_svg_estabilidade(projeto, resultado), encoding="utf-8")

    if args.zip:
        p_zip = Path(args.zip)
        itens_zip = [
            ("entrada.json", codificar_resultado_json_str(resultado).encode("utf-8")),
            ("resultado.json", codificar_resultado_json_str(resultado).encode("utf-8")),
            ("laudo_tecnico.md", gerar_laudo_geotecnico_markdown(resultado).encode("utf-8")),
            ("resumo_estabilidade.csv", gerar_resumo_csv_str(resultado).encode("utf-8")),
            ("fatias_detalhadas.csv", gerar_fatias_csv_str(resultado).encode("utf-8")),
            ("painel_estabilidade.svg", gerar_svg_estabilidade(projeto, resultado).encode("utf-8")),
        ]
        criar_pacote_zip_deterministico(p_zip, itens_zip)

    if not args.silencioso:
        sys.stdout.write("================================================================================\n")
        sys.stdout.write(f" LAUDO GEOTÉCNICO DE ESTABILIDADE DE TALUDES — ABNT NBR 11682:2009\n")
        sys.stdout.write(" LOFRANO TECNOLOGIA (Zero Float, Aritmética Racional Exata)\n")
        sys.stdout.write("================================================================================\n")
        sys.stdout.write(f"Talude: {resultado.nome_talude}\n")
        sys.stdout.write(f"Nível de Segurança: {resultado.nivel_seguranca} (FS mín. exigido: {formatar_fracao_decimal(resultado.fs_minimo_exigido)})\n")
        sys.stdout.write("--------------------------------------------------------------------------------\n")
        sys.stdout.write(f"Fator de Segurança (Bishop Simplificado): {formatar_fracao_decimal(resultado.fator_seguranca_bishop)} ({resultado.iteracoes_bishop} iterações)\n")
        sys.stdout.write(f"Fator de Segurança (Fellenius Ordinário): {formatar_fracao_decimal(resultado.fator_seguranca_fellenius)}\n")
        sys.stdout.write(f"Diagnóstico Normativo: {resultado.diagnostico}\n")
        sys.stdout.write(f"Status da Conformidade: {'CONFORME' if resultado.conforme_nbr11682 else 'NÃO CONFORME'}\n")
        sys.stdout.write("--------------------------------------------------------------------------------\n")
        sys.stdout.write(f"Peso Total do Maciço Deslizante: {formatar_forca_kn(resultado.peso_total_maciço_n)}\n")
        sys.stdout.write(f"Momento Atuante Total (Mat): {resultado.momento_atuante_total_nm:,} N·m\n".replace(",", "."))
        sys.stdout.write(f"Momento Resistente Bishop (Mres): {resultado.momento_resistente_bishop_nm:,} N·m\n".replace(",", "."))
        sys.stdout.write(f"Lamelas Analisadas: {len(resultado.fatias)}\n")
        sys.stdout.write("================================================================================\n")

    return 0 if resultado.conforme_nbr11682 else 1


def comando_exemplo(args: argparse.Namespace) -> int:
    """Gera o arquivo de exemplo de talude rodoviário."""
    from .codecs import codificar_talude_json_str
    talude_ex = gerar_exemplo_talude()
    json_str = codificar_talude_json_str(talude_ex)

    if args.saida:
        p_saida = Path(args.saida)
        p_saida.write_text(json_str, encoding="utf-8")
        sys.stdout.write(f"Exemplo gravado com sucesso em '{p_saida}'.\n")
    else:
        sys.stdout.write(json_str + "\n")
    return 0


def comando_tabelas(args: argparse.Namespace) -> int:
    """Exibe as tabelas de referência da NBR 11682 e parâmetros de solos."""
    sys.stdout.write("================================================================================\n")
    sys.stdout.write(" TABELAS REGULAMENTARES — ABNT NBR 11682:2009\n")
    sys.stdout.write("================================================================================\n\n")

    sys.stdout.write("1. NÍVEIS DE SEGURANÇA E FATORES DE SEGURANÇA MÍNIMOS (TABELA 1):\n")
    sys.stdout.write("--------------------------------------------------------------------------------\n")
    for codigo, info in NIVEIS_SEGURANCA.items():
        fs_str = formatar_fracao_decimal(info.fs_minimo_fracao)
        sys.stdout.write(f"• {codigo:<8} | FS Mínimo: {fs_str:<6} | {info.descricao}\n")

    sys.stdout.write("\n2. SOLOS DE REFERÊNCIA BRASILEIROS TÍPICOS:\n")
    sys.stdout.write("--------------------------------------------------------------------------------\n")
    for codigo, s in SOLOS_REFERENCIA.items():
        sys.stdout.write(
            f"• {s.nome:<38} | γ = {s.peso_especifico_kn_m3} kN/m³ | c' = {s.coesao_efetiva_kpa:>2} kPa | φ' = {s.angulo_atrito_graus}°\n"
        )
    sys.stdout.write("================================================================================\n")
    return 0


def comando_versao(args: argparse.Namespace) -> int:
    """Exibe a versão instalada do software."""
    sys.stdout.write(f"calculo-estabilidade-taludes-nbr11682 {__version__}\n")
    sys.stdout.write("LOFRANO TECNOLOGIA — Engenharia Geotécnica Determinística\n")
    return 0


def criar_parser() -> argparse.ArgumentParser:
    """Cria o analisador de argumentos da CLI."""
    parser = argparse.ArgumentParser(
        prog="estabilidade-taludes",
        description="Cálculo determinístico de estabilidade de taludes e encostas segundo a ABNT NBR 11682:2009.",
    )
    subparsers = parser.add_subparsers(dest="subcomando", title="Subcomandos disponíveis")

    # Subcomando 'calcular'
    parser_calc = subparsers.add_parser("calcular", help="Calcula a estabilidade de um talude a partir de arquivo JSON.")
    parser_calc.add_argument("arquivo_json", help="Caminho para o arquivo JSON contendo os dados do talude.")
    parser_calc.add_argument("--saida-json", help="Caminho para salvar o resultado em formato JSON.")
    parser_calc.add_argument("--saida-csv-resumo", help="Caminho para salvar resumo em CSV.")
    parser_calc.add_argument("--saida-csv-fatias", help="Caminho para salvar tabela de fatias em CSV.")
    parser_calc.add_argument("--saida-md", help="Caminho para salvar o laudo técnico em Markdown.")
    parser_calc.add_argument("--saida-svg", help="Caminho para salvar o painel gráfico em SVG.")
    parser_calc.add_argument("--zip", help="Caminho para gerar pacote ZIP determinístico com todos os laudos.")
    parser_calc.add_argument("--silencioso", action="store_true", help="Suprime saída no terminal.")

    # Subcomando 'exemplo'
    parser_ex = subparsers.add_parser("exemplo", help="Gera arquivo JSON de exemplo de talude rodoviário.")
    parser_ex.add_argument("--saida", "-o", help="Caminho de saída para gravar o arquivo JSON.")

    # Subcomando 'tabelas'
    subparsers.add_parser("tabelas", help="Exibe níveis de segurança e parâmetros de solos de referência.")

    # Subcomando 'versao'
    subparsers.add_parser("versao", help="Exibe a versão do programa.")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Ponto de entrada principal da linha de comando."""
    parser = criar_parser()
    args = parser.parse_args(argv)

    if not args.subcomando:
        parser.print_help()
        return 0

    if args.subcomando == "calcular":
        return comando_calcular(args)
    elif args.subcomando == "exemplo":
        return comando_exemplo(args)
    elif args.subcomando == "tabelas":
        return comando_tabelas(args)
    elif args.subcomando == "versao":
        return comando_versao(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
