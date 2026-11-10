"""Testes unitários da interface CLI de estabilidade de taludes (NBR 11682).

LOFRANO TECNOLOGIA.
"""

import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from estabilidade_taludes import __version__
from estabilidade_taludes.cli import main


class TestCLI(unittest.TestCase):
    """Bateria de testes para todos os subcomandos e opções da CLI."""

    def setUp(self):
        self.exemplar = Path(__file__).parent.parent / "exemplares" / "talude_rodoviario_padrao.json"

    def test_cli_sem_argumentos_retorna_zero(self):
        with patch("sys.stdout", new=io.StringIO()):
            ret = main([])
            self.assertEqual(ret, 0)

    def test_cli_versao(self):
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            ret = main(["versao"])
            self.assertEqual(ret, 0)
            self.assertIn(__version__, fake_out.getvalue())
            self.assertIn("LOFRANO TECNOLOGIA", fake_out.getvalue())

    def test_cli_tabelas(self):
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            ret = main(["tabelas"])
            self.assertEqual(ret, 0)
            self.assertIn("ABNT NBR 11682:2009", fake_out.getvalue())
            self.assertIn("ALTO", fake_out.getvalue())
            self.assertIn("Argila mole", fake_out.getvalue())

    def test_cli_exemplo_stdout(self):
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            ret = main(["exemplo"])
            self.assertEqual(ret, 0)
            self.assertIn("Talude de Corte Rodoviário", fake_out.getvalue())

    def test_cli_exemplo_arquivo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            caminho_out = Path(tmpdir) / "exemplo_gerado.json"
            ret = main(["exemplo", "--saida", str(caminho_out)])
            self.assertEqual(ret, 0)
            self.assertTrue(caminho_out.exists())

    def test_cli_calcular_arquivo_inexistente(self):
        with patch("sys.stderr", new=io.StringIO()):
            ret = main(["calcular", "/caminho/fantasma/talude.json"])
            self.assertEqual(ret, 2)

    def test_cli_calcular_exemplar_sucesso(self):
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            ret = main(["calcular", str(self.exemplar)])
            self.assertEqual(ret, 0)
            saida = fake_out.getvalue()
            self.assertIn("LAUDO GEOTÉCNICO DE ESTABILIDADE", saida)
            self.assertIn("Bishop Simplificado", saida)
            self.assertIn("CONFORME", saida)

    def test_cli_calcular_com_arquivos_saida(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p_json = Path(tmpdir) / "res.json"
            p_csv_res = Path(tmpdir) / "res.csv"
            p_csv_fat = Path(tmpdir) / "fat.csv"
            p_md = Path(tmpdir) / "laudo.md"
            p_svg = Path(tmpdir) / "painel.svg"
            p_zip = Path(tmpdir) / "pacote.zip"

            ret = main([
                "calcular",
                str(self.exemplar),
                "--saida-json", str(p_json),
                "--saida-csv-resumo", str(p_csv_res),
                "--saida-csv-fatias", str(p_csv_fat),
                "--saida-md", str(p_md),
                "--saida-svg", str(p_svg),
                "--zip", str(p_zip),
                "--silencioso",
            ])
            self.assertEqual(ret, 0)
            self.assertTrue(p_json.exists())
            self.assertTrue(p_csv_res.exists())
            self.assertTrue(p_csv_fat.exists())
            self.assertTrue(p_md.exists())
            self.assertTrue(p_svg.exists())
            self.assertTrue(p_zip.exists())


if __name__ == "__main__":
    unittest.main()
