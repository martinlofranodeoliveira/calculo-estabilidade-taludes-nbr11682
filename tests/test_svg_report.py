"""Testes unitários da geração do painel em SVG (NBR 11682).

LOFRANO TECNOLOGIA.
"""

from fractions import Fraction
import unittest

from estabilidade_taludes.domain import (
    CirculoRuptura,
    FatiaDiscretizada,
    Ponto2D,
    PropriedadesSolo,
    ResultadoEstabilidade,
    TaludeInput,
)
from estabilidade_taludes.svg_report import gerar_svg_estabilidade


class TestSvgReport(unittest.TestCase):
    """Validação da saída visual em SVG."""

    def test_gerar_svg_dimensoes_e_elementos(self):
        perfil = [Ponto2D(0, 0), Ponto2D(20000, 10000), Ponto2D(40000, 10000)]
        circ = CirculoRuptura(20000, 25000, 20000)
        solo = PropriedadesSolo("Solo Residual", 18500, 20000, 26)
        projeto = TaludeInput("Talude Alpha", "Desc", "ALTO", perfil, circ, solo)

        fatia = FatiaDiscretizada(
            1, 15000, 2000, 8000, 5000, 3000, 20, 100000, 0, 35000, 55000
        )
        res = ResultadoEstabilidade(
            nome_talude="Talude Alpha",
            descricao="Desc",
            nivel_seguranca="ALTO",
            fs_minimo_exigido=Fraction(3, 2),
            fator_seguranca_fellenius=Fraction(155, 100),
            fator_seguranca_bishop=Fraction(165, 100),
            peso_total_maciço_n=100000,
            momento_atuante_total_nm=700000,
            momento_resistente_fellenius_nm=1100000,
            momento_resistente_bishop_nm=1155000,
            fatias=[fatia],
            conforme_nbr11682=True,
            diagnostico="ESTÁVEL (APROVADO PELA NBR 11682)",
            iteracoes_bishop=4,
        )

        svg = gerar_svg_estabilidade(projeto, res)
        self.assertIn('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 900"', svg)
        self.assertIn("LOFRANO TECNOLOGIA", svg)
        self.assertIn("Talude Alpha", svg)
        self.assertIn("CONFORME NBR 11682", svg)
        self.assertIn("BISHOP SIMPLIFICADO", svg)
        self.assertIn("FELLENIUS ORDINÁRIO", svg)
        self.assertIn("1,650", svg)


if __name__ == "__main__":
    unittest.main()
