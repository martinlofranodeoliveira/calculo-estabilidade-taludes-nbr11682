"""Testes unitários dos modelos de domínio e formatadores (NBR 11682).

LOFRANO TECNOLOGIA.
"""

from fractions import Fraction
import unittest

from estabilidade_taludes.domain import (
    CirculoRuptura,
    Ponto2D,
    PropriedadesSolo,
    TaludeInput,
    formatar_comprimento_m,
    formatar_forca_kn,
    formatar_fracao_decimal,
    formatar_pressao_kpa,
)
from estabilidade_taludes.errors import ErroValidacaoGeotecnica


class TestModelosDominio(unittest.TestCase):
    """Bateria de testes para validação e comportamento de modelos de dados."""

    def test_ponto_2d_valido(self):
        p = Ponto2D(x_mm=1000, y_mm=2500)
        self.assertEqual(p.x_mm, 1000)
        self.assertEqual(p.y_mm, 2500)

    def test_ponto_2d_invalido(self):
        with self.assertRaises(ErroValidacaoGeotecnica):
            Ponto2D(x_mm="1000", y_mm=2000)  # type: ignore

    def test_propriedades_solo_validas(self):
        solo = PropriedadesSolo("Argila", 18000, 20000, 25)
        self.assertEqual(solo.nome_camada, "Argila")
        self.assertEqual(solo.peso_especifico_n_m3, 18000)
        self.assertEqual(solo.coesao_efetiva_pa, 20000)
        self.assertEqual(solo.angulo_atrito_graus, 25)

    def test_propriedades_solo_invalidas(self):
        with self.assertRaises(ErroValidacaoGeotecnica):
            PropriedadesSolo("", 18000, 20000, 25)
        with self.assertRaises(ErroValidacaoGeotecnica):
            PropriedadesSolo("Solo", -10, 20000, 25)
        with self.assertRaises(ErroValidacaoGeotecnica):
            PropriedadesSolo("Solo", 18000, -500, 25)
        with self.assertRaises(ErroValidacaoGeotecnica):
            PropriedadesSolo("Solo", 18000, 20000, 50)  # > 45 graus

    def test_circulo_ruptura_valido(self):
        c = CirculoRuptura(10000, 20000, 15000)
        self.assertEqual(c.raio_mm, 15000)

    def test_circulo_ruptura_invalido(self):
        with self.assertRaises(ErroValidacaoGeotecnica):
            CirculoRuptura(10000, 20000, 0)
        with self.assertRaises(ErroValidacaoGeotecnica):
            CirculoRuptura(10000, 20000, -5000)

    def test_talude_input_perfil_insuficiente(self):
        solo = PropriedadesSolo("Solo", 18000, 10000, 20)
        circ = CirculoRuptura(10000, 20000, 15000)
        with self.assertRaises(ErroValidacaoGeotecnica):
            TaludeInput(
                nome_talude="Talude",
                descricao="Desc",
                nivel_seguranca_nbr11682="ALTO",
                perfil_terreno=[Ponto2D(0, 0)],
                circulo_tentativa=circ,
                solo=solo,
            )

    def test_talude_input_perfil_nao_crescente(self):
        solo = PropriedadesSolo("Solo", 18000, 10000, 20)
        circ = CirculoRuptura(10000, 20000, 15000)
        with self.assertRaises(ErroValidacaoGeotecnica):
            TaludeInput(
                nome_talude="Talude",
                descricao="Desc",
                nivel_seguranca_nbr11682="ALTO",
                perfil_terreno=[Ponto2D(1000, 0), Ponto2D(500, 1000)],
                circulo_tentativa=circ,
                solo=solo,
            )

    def test_talude_input_nivel_invalido(self):
        solo = PropriedadesSolo("Solo", 18000, 10000, 20)
        circ = CirculoRuptura(10000, 20000, 15000)
        with self.assertRaises(ErroValidacaoGeotecnica):
            TaludeInput(
                nome_talude="Talude",
                descricao="Desc",
                nivel_seguranca_nbr11682="INEXISTENTE",
                perfil_terreno=[Ponto2D(0, 0), Ponto2D(1000, 1000)],
                circulo_tentativa=circ,
                solo=solo,
            )

    def test_talude_input_fatias_fora_faixa(self):
        solo = PropriedadesSolo("Solo", 18000, 10000, 20)
        circ = CirculoRuptura(10000, 20000, 15000)
        with self.assertRaises(ErroValidacaoGeotecnica):
            TaludeInput(
                nome_talude="Talude",
                descricao="Desc",
                nivel_seguranca_nbr11682="MEDIO",
                perfil_terreno=[Ponto2D(0, 0), Ponto2D(1000, 1000)],
                circulo_tentativa=circ,
                solo=solo,
                numero_fatias=2,  # < 4
            )


class TestFormatadores(unittest.TestCase):
    """Testes unitários dos formatadores decimais e unidades métricas."""

    def test_formatar_fracao_decimal(self):
        self.assertEqual(formatar_fracao_decimal(Fraction(3, 2)), "1,500")
        self.assertEqual(formatar_fracao_decimal(Fraction(7, 5)), "1,400")
        self.assertEqual(formatar_fracao_decimal(Fraction(1, 3)), "0,333")
        self.assertEqual(formatar_fracao_decimal(Fraction(0, 1)), "0,000")
        self.assertEqual(formatar_fracao_decimal(Fraction(-3, 2)), "-1,500")

    def test_formatar_comprimento_m(self):
        self.assertEqual(formatar_comprimento_m(12000), "12,00 m")
        self.assertEqual(formatar_comprimento_m(550), "0,55 m")
        self.assertEqual(formatar_comprimento_m(-3000), "-3,00 m")

    def test_formatar_pressao_kpa(self):
        self.assertEqual(formatar_pressao_kpa(15000), "15,00 kPa")
        self.assertEqual(formatar_pressao_kpa(750), "0,75 kPa")
        self.assertEqual(formatar_pressao_kpa(0), "0,00 kPa")

    def test_formatar_forca_kn(self):
        self.assertEqual(formatar_forca_kn(125000), "125,00 kN")
        self.assertEqual(formatar_forca_kn(500), "0,50 kN")
        self.assertEqual(formatar_forca_kn(-50000), "-50,00 kN")


if __name__ == "__main__":
    unittest.main()
