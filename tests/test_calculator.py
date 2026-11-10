"""Testes unitários do motor de cálculo de estabilidade (NBR 11682).

LOFRANO TECNOLOGIA.
"""

from fractions import Fraction
import unittest

from estabilidade_taludes.calculator import (
    calcular_estabilidade_talude,
    graus_por_seno,
    obter_cota_terreno_mm,
)
from estabilidade_taludes.domain import (
    CirculoRuptura,
    Ponto2D,
    PropriedadesSolo,
    TaludeInput,
)
from estabilidade_taludes.errors import ErroGeometriaCirculo


class TestCalculadoraEstabilidade(unittest.TestCase):
    """Testes de interpolação geométrica e cálculo de equilíbrio limite."""

    def setUp(self):
        self.perfil = [
            Ponto2D(0, 10000),
            Ponto2D(20000, 10000),
            Ponto2D(40000, 20000),
            Ponto2D(60000, 20000),
        ]
        self.solo = PropriedadesSolo("Argila arenosa", 18000, 20000, 25)
        self.circulo = CirculoRuptura(centro_x_mm=30000, centro_y_mm=35000, raio_mm=26000)

    def test_obter_cota_terreno_mm(self):
        # Antes do início e depois do fim
        self.assertEqual(obter_cota_terreno_mm(self.perfil, -1000), 10000)
        self.assertEqual(obter_cota_terreno_mm(self.perfil, 70000), 20000)
        # No trecho plano inicial
        self.assertEqual(obter_cota_terreno_mm(self.perfil, 10000), 10000)
        # Na rampa intermediária (ponto médio 30000 -> cota 15000)
        self.assertEqual(obter_cota_terreno_mm(self.perfil, 30000), 15000)
        # No topo plano final
        self.assertEqual(obter_cota_terreno_mm(self.perfil, 50000), 20000)

    def test_graus_por_seno(self):
        self.assertEqual(graus_por_seno(Fraction(0, 1)), 0)
        self.assertEqual(graus_por_seno(Fraction(1, 2)), 30)
        self.assertEqual(graus_por_seno(Fraction(-1, 2)), -30)
        self.assertEqual(graus_por_seno(Fraction(1, 1)), 90)
        self.assertEqual(graus_por_seno(Fraction(-1, 1)), -90)

    def test_circulo_fora_dos_limites(self):
        circ_fora = CirculoRuptura(centro_x_mm=200000, centro_y_mm=250000, raio_mm=10000)
        proj = TaludeInput("Talude", "D", "ALTO", self.perfil, circ_fora, self.solo)
        with self.assertRaises(ErroGeometriaCirculo):
            calcular_estabilidade_talude(proj)

    def test_circulo_totalmente_acima(self):
        circ_acima = CirculoRuptura(centro_x_mm=30000, centro_y_mm=80000, raio_mm=10000)
        proj = TaludeInput("Talude", "D", "ALTO", self.perfil, circ_acima, self.solo)
        with self.assertRaises(ErroGeometriaCirculo):
            calcular_estabilidade_talude(proj)

    def test_circulo_extensao_insuficiente(self):
        circ_raso = CirculoRuptura(centro_x_mm=30000, centro_y_mm=15499, raio_mm=500)
        proj = TaludeInput("Talude", "D", "ALTO", self.perfil, circ_raso, self.solo)
        with self.assertRaises(ErroGeometriaCirculo):
            calcular_estabilidade_talude(proj)

    def test_calculo_talude_estavel(self):
        proj = TaludeInput(
            nome_talude="Talude Padrão",
            descricao="Talude de rodovia com solo resistente",
            nivel_seguranca_nbr11682="ALTO",
            perfil_terreno=self.perfil,
            circulo_tentativa=self.circulo,
            solo=self.solo,
            numero_fatias=12,
        )
        res = calcular_estabilidade_talude(proj)
        self.assertTrue(res.conforme_nbr11682)
        self.assertGreater(res.fator_seguranca_bishop, Fraction(3, 2))
        self.assertGreater(res.fator_seguranca_fellenius, Fraction(1, 1))
        self.assertGreater(len(res.fatias), 5)
        self.assertIn("ESTÁVEL", res.diagnostico)

    def test_calculo_talude_instavel(self):
        # Solo fraco sem coesão e ângulo muito baixo em rampa inclinada
        solo_fraco = PropriedadesSolo("Solo Muito Fraco", 19000, 1000, 8)
        proj_instavel = TaludeInput(
            nome_talude="Talude Instável",
            descricao="Risco iminente",
            nivel_seguranca_nbr11682="ALTO",
            perfil_terreno=self.perfil,
            circulo_tentativa=self.circulo,
            solo=solo_fraco,
            numero_fatias=12,
        )
        res = calcular_estabilidade_talude(proj_instavel)
        self.assertFalse(res.conforme_nbr11682)
        self.assertLess(res.fator_seguranca_bishop, Fraction(3, 2))

    def test_efeito_lencol_freatico(self):
        proj_seco = TaludeInput(
            nome_talude="Talude Seco",
            descricao="Sem água",
            nivel_seguranca_nbr11682="ALTO",
            perfil_terreno=self.perfil,
            circulo_tentativa=self.circulo,
            solo=self.solo,
            numero_fatias=12,
            nivel_dagua_y_mm=None,
        )
        res_seco = calcular_estabilidade_talude(proj_seco)

        proj_umido = TaludeInput(
            nome_talude="Talude Saturado",
            descricao="Com nível d'água alto",
            nivel_seguranca_nbr11682="ALTO",
            perfil_terreno=self.perfil,
            circulo_tentativa=self.circulo,
            solo=self.solo,
            numero_fatias=12,
            nivel_dagua_y_mm=16000,
        )
        res_umido = calcular_estabilidade_talude(proj_umido)

        # A poropressão da água reduz o fator de segurança
        self.assertGreater(res_seco.fator_seguranca_bishop, res_umido.fator_seguranca_bishop)

    def test_calculo_diferentes_niveis_seguranca(self):
        for nivel, fs_esperado in [("ALTO", Fraction(3, 2)), ("MEDIO", Fraction(7, 5)), ("BAIXO", Fraction(13, 10))]:
            proj = TaludeInput("Talude", "D", nivel, self.perfil, self.circulo, self.solo, 8)
            res = calcular_estabilidade_talude(proj)
            self.assertEqual(res.fs_minimo_exigido, fs_esperado)

    def test_equilibrio_momento_e_forcas(self):
        proj = TaludeInput("Talude", "D", "ALTO", self.perfil, self.circulo, self.solo, 10)
        res = calcular_estabilidade_talude(proj)
        self.assertGreater(res.momento_atuante_total_nm, 0)
        self.assertGreater(res.momento_resistente_bishop_nm, 0)
        self.assertGreater(res.peso_total_maciço_n, 0)
        self.assertGreater(res.iteracoes_bishop, 0)

    def test_variacao_numero_fatias(self):
        for num_fatias in [4, 8, 16, 25]:
            proj = TaludeInput("Talude", "D", "ALTO", self.perfil, self.circulo, self.solo, num_fatias)
            res = calcular_estabilidade_talude(proj)
            self.assertGreater(len(res.fatias), 2)
            self.assertGreater(res.fator_seguranca_bishop, 0)

    def test_graus_por_seno_extremos(self):
        self.assertEqual(graus_por_seno(Fraction(2, 1)), 90)
        self.assertEqual(graus_por_seno(Fraction(-2, 1)), -90)
        self.assertEqual(graus_por_seno(Fraction(86602540, 100000000)), 60)
        self.assertEqual(graus_por_seno(Fraction(70710678, 100000000)), 45)

    def test_diagnostico_estados(self):
        # Caso marginal
        solo_medio = PropriedadesSolo("Solo Médio", 19000, 5000, 14)
        proj = TaludeInput("Talude", "D", "ALTO", self.perfil, self.circulo, solo_medio, 10)
        res = calcular_estabilidade_talude(proj)
        if res.fator_seguranca_bishop < Fraction(3, 2):
            self.assertIn("NÃO CONFORME", res.diagnostico)


if __name__ == "__main__":
    unittest.main()
