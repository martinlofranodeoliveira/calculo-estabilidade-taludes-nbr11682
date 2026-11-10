"""Testes unitários dos módulos de exportação e segurança CSV/ZIP (NBR 11682).

LOFRANO TECNOLOGIA.
"""

from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
import zipfile

from estabilidade_taludes.domain import (
    FatiaDiscretizada,
    ResultadoEstabilidade,
)
from estabilidade_taludes.errors import ErroExportacao
from estabilidade_taludes.exports import (
    criar_pacote_zip_deterministico,
    gerar_fatias_csv_str,
    gerar_laudo_geotecnico_markdown,
    gerar_resumo_csv_str,
    sanitizar_campo_csv,
)


class TestExportacoes(unittest.TestCase):
    """Testes de geração de CSV protegido contra injeção e empacotamento determinístico."""

    def setUp(self):
        self.fatia = FatiaDiscretizada(
            indice=1,
            x_central_mm=10000,
            largura_mm=2000,
            y_topo_mm=15000,
            y_base_mm=8000,
            altura_media_mm=7000,
            inclinacao_base_graus=22,
            peso_fatia_n=250000,
            poropressao_base_pa=5000,
            forca_atuante_tangencial_n=93000,
            forca_resistente_fellenius_n=145000,
        )
        self.resultado = ResultadoEstabilidade(
            nome_talude="Talude Teste",
            descricao="Descricao",
            nivel_seguranca="ALTO",
            fs_minimo_exigido=Fraction(3, 2),
            fator_seguranca_fellenius=Fraction(155, 100),
            fator_seguranca_bishop=Fraction(170, 100),
            peso_total_maciço_n=250000,
            momento_atuante_total_nm=930000,
            momento_resistente_fellenius_nm=1450000,
            momento_resistente_bishop_nm=1580000,
            fatias=[self.fatia],
            conforme_nbr11682=True,
            diagnostico="ESTÁVEL",
            iteracoes_bishop=5,
        )

    def test_sanitizacao_formula_csv(self):
        self.assertEqual(sanitizar_campo_csv("=SUM(A1:A10)"), "'=SUM(A1:A10)")
        self.assertEqual(sanitizar_campo_csv("+12345"), "'+12345")
        self.assertEqual(sanitizar_campo_csv("-cmd|' /C calc'!A0"), "'-cmd|' /C calc'!A0")
        self.assertEqual(sanitizar_campo_csv("@HYPERLINK()"), "'@HYPERLINK()")
        self.assertEqual(sanitizar_campo_csv("TextoNormal"), "TextoNormal")

    def test_gerar_fatias_csv(self):
        csv_str = gerar_fatias_csv_str(self.resultado)
        linhas = csv_str.strip().split("\n")
        self.assertGreaterEqual(len(linhas), 2)
        cabecalho = linhas[0].split(";")
        self.assertEqual(cabecalho[0], "Fatia")
        self.assertEqual(cabecalho[1], "X_Central_m")
        # Dados da fatia 1
        dados_f1 = linhas[1].split(";")
        self.assertEqual(dados_f1[0], "1")
        self.assertIn("10,00 m", dados_f1[1])

    def test_gerar_resumo_csv(self):
        csv_str = gerar_resumo_csv_str(self.resultado)
        self.assertIn("Bishop Simplificado", csv_str)
        self.assertIn("Fellenius (Ordinário)", csv_str)
        self.assertIn("APROVADO", csv_str)

    def test_gerar_laudo_markdown(self):
        md_str = gerar_laudo_geotecnico_markdown(self.resultado)
        self.assertIn("# Laudo Técnico de Estabilidade de Taludes e Encostas — NBR 11682", md_str)
        self.assertIn("LOFRANO TECNOLOGIA", md_str)
        self.assertIn("ESTÁVEL", md_str)
        self.assertIn("Bishop Simplificado", md_str)

    def test_pacote_zip_deterministico(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            caminho_zip = Path(tmpdir) / "laudo_deterministico.zip"
            itens = [
                ("arquivo1.txt", b"Conteudo 1"),
                ("pasta/arquivo2.txt", b"Conteudo 2"),
            ]
            criar_pacote_zip_deterministico(caminho_zip, itens)
            self.assertTrue(caminho_zip.exists())

            # Verificar timestamp fixo determinístico 2026-01-01
            with zipfile.ZipFile(caminho_zip, "r") as zf:
                infos = zf.infolist()
                self.assertEqual(len(infos), 2)
                for info in infos:
                    self.assertEqual(info.date_time, (2026, 1, 1, 0, 0, 0))

            # Testar bloqueio contra sobrescrita
            with self.assertRaises(ErroExportacao):
                criar_pacote_zip_deterministico(caminho_zip, itens)


if __name__ == "__main__":
    unittest.main()
