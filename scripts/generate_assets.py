#!/usr/bin/env python3
"""Gera artefatos visuais (SVG e PNG via Chrome Headless), relatórios e arquivos de release.

LOFRANO TECNOLOGIA.
"""

import hashlib
import os
from pathlib import Path
import subprocess
import sys

# Adicionar src ao sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from estabilidade_taludes.calculator import calcular_estabilidade_talude
from estabilidade_taludes.codecs import (
    carregar_talude,
    resultado_para_dict,
    serializar_json_canonico,
)
from estabilidade_taludes.exports import (
    criar_pacote_zip_deterministico,
    gerar_fatias_csv_str,
    gerar_laudo_geotecnico_markdown,
    gerar_resumo_csv_str,
)
from estabilidade_taludes.svg_report import gerar_svg_estabilidade


def main() -> int:
    raiz = Path(__file__).resolve().parent.parent
    exemplar = raiz / "exemplares" / "talude_rodoviario_padrao.json"
    docs_dir = raiz / "docs"
    docs_dir.mkdir(exist_ok=True)
    release_dir = raiz / "release" / "v1.0.0"
    release_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Processando cenário exemplar: {exemplar}")
    entrada = carregar_talude(exemplar)
    resultado = calcular_estabilidade_talude(entrada)

    # 1. Gerar SVG
    svg_conteudo = gerar_svg_estabilidade(entrada, resultado)
    svg_path = docs_dir / "exemplo.svg"
    svg_path.write_text(svg_conteudo, encoding="utf-8")
    print(f"[OK] SVG gerado: {svg_path}")

    # 2. Renderizar PNG via Chrome Headless em 1440x900
    png_path = docs_dir / "exemplo.png"
    print("[*] Renderizando PNG 1440x900 via Chrome headless...")
    cmd_chrome = [
        "google-chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--window-size=1440,900",
        f"--screenshot={png_path}",
        str(svg_path.resolve()),
    ]
    res = subprocess.run(cmd_chrome, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Aviso: google-chrome retornou {res.returncode}: {res.stderr}", file=sys.stderr)
        cmd_chromium = [
            "chromium",
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--window-size=1440,900",
            f"--screenshot={png_path}",
            str(svg_path.resolve()),
        ]
        res2 = subprocess.run(cmd_chromium, capture_output=True, text=True)
        if res2.returncode != 0:
            print(f"Falha ao gerar screenshot com chromium: {res2.stderr}", file=sys.stderr)
    print(f"[OK] PNG gerado: {png_path} ({png_path.stat().st_size} bytes)")

    # 3. Gerar pacote ZIP determinístico
    zip_path = release_dir / "exemplo-estabilidade-talude.zip"
    if zip_path.exists():
        zip_path.unlink()

    fatias_csv_bytes = gerar_fatias_csv_str(resultado).encode("utf-8")
    resumo_csv_bytes = gerar_resumo_csv_str(resultado).encode("utf-8")
    res_dict = resultado_para_dict(resultado)
    res_json_bytes = serializar_json_canonico(res_dict).encode("utf-8")
    laudo_md_bytes = gerar_laudo_geotecnico_markdown(resultado).encode("utf-8")

    arquivos_zip = [
        ("entrada_talude.json", exemplar.read_bytes()),
        ("resultado_estabilidade.json", res_json_bytes),
        ("resumo_estabilidade.csv", resumo_csv_bytes),
        ("fatias_detalhadas.csv", fatias_csv_bytes),
        ("laudo_tecnico.md", laudo_md_bytes),
        ("painel_estabilidade.svg", svg_conteudo.encode("utf-8")),
    ]
    criar_pacote_zip_deterministico(zip_path, arquivos_zip)
    print(f"[OK] ZIP determinístico gerado: {zip_path}")

    # Copiar PNG para a pasta de release
    rel_png = release_dir / "exemplo.png"
    rel_png.write_bytes(png_path.read_bytes())

    # 4. Construir wheel e sdist
    print("[*] Construindo pacotes com setuptools.build_meta...")
    dist_dir = raiz / "dist"
    dist_dir.mkdir(exist_ok=True)
    for antigo in dist_dir.glob("*"):
        antigo.unlink()

    os.chdir(raiz)
    import setuptools.build_meta as b
    b.build_sdist(str(dist_dir))
    b.build_wheel(str(dist_dir))
    for item in dist_dir.glob("*"):
        alvo = release_dir / item.name
        alvo.write_bytes(item.read_bytes())
        print(f"[OK] Pacote copiado para release: {alvo.name}")

    # 5. Gerar SHA256SUMS
    print("[*] Gerando SHA256SUMS...")
    linhas_sha = []
    for p in sorted(release_dir.iterdir()):
        if p.name == "SHA256SUMS":
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        linhas_sha.append(f"{h}  {p.name}")

    sha_file = release_dir / "SHA256SUMS"
    sha_file.write_text("\n".join(linhas_sha) + "\n", encoding="utf-8")
    print(f"[OK] SHA256SUMS gerado em: {sha_file}")
    print(sha_file.read_text(encoding="utf-8"))

    return 0


if __name__ == "__main__":
    sys.exit(main())
