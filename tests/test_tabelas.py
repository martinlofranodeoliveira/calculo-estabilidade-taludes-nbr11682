"""Testes das tabelas da NBR 11682 e funções trigonométricas racionais.

LOFRANO TECNOLOGIA.
"""

from fractions import Fraction
import unittest

from estabilidade_taludes.tabelas_nbr11682 import (
    NIVEIS_SEGURANCA,
    SOLOS_REFERENCIA,
    obter_cosseno_graus_racional,
    obter_seno_graus_racional,
    obter_tangente_graus_racional,
)


class TestTabelasNBR11682(unittest.TestCase):
    """Validação das tabelas normativas e constantes trigonométricas."""

    def test_niveis_seguranca_completos(self):
        self.assertIn("ALTO", NIVEIS_SEGURANCA)
        self.assertIn("MEDIO", NIVEIS_SEGURANCA)
        self.assertIn("BAIXO", NIVEIS_SEGURANCA)

        self.assertEqual(NIVEIS_SEGURANCA["ALTO"].fs_minimo_fracao, Fraction(3, 2))
        self.assertEqual(NIVEIS_SEGURANCA["MEDIO"].fs_minimo_fracao, Fraction(7, 5))
        self.assertEqual(NIVEIS_SEGURANCA["BAIXO"].fs_minimo_fracao, Fraction(13, 10))

    def test_solos_referencia(self):
        self.assertGreaterEqual(len(SOLOS_REFERENCIA), 5)
        for s in SOLOS_REFERENCIA.values():
            self.assertGreater(s.peso_especifico_kn_m3, 0)
            self.assertGreaterEqual(s.coesao_efetiva_kpa, 0)
            self.assertGreaterEqual(s.angulo_atrito_graus, 0)
            self.assertLessEqual(s.angulo_atrito_graus, 45)

    def test_trigonometria_seno_notaveis(self):
        s0 = obter_seno_graus_racional(0)
        s30 = obter_seno_graus_racional(30)
        s90 = obter_seno_graus_racional(90)
        s_neg30 = obter_seno_graus_racional(-30)

        self.assertEqual(s0, Fraction(0, 1))
        self.assertEqual(s30, Fraction(50_000_000, 100_000_000))
        self.assertEqual(s90, Fraction(100_000_000, 100_000_000))
        self.assertEqual(s_neg30, Fraction(-50_000_000, 100_000_000))

    def test_trigonometria_cosseno_notaveis(self):
        c0 = obter_cosseno_graus_racional(0)
        c60 = obter_cosseno_graus_racional(60)
        c90 = obter_cosseno_graus_racional(90)
        c_neg60 = obter_cosseno_graus_racional(-60)

        self.assertEqual(c0, Fraction(100_000_000, 100_000_000))
        self.assertEqual(c60, Fraction(50_000_000, 100_000_000))
        self.assertEqual(c90, Fraction(0, 1))
        self.assertEqual(c_neg60, Fraction(50_000_000, 100_000_000))

    def test_trigonometria_tangente_notaveis(self):
        t0 = obter_tangente_graus_racional(0)
        t45 = obter_tangente_graus_racional(45)
        t_neg45 = obter_tangente_graus_racional(-45)

        self.assertEqual(t0, Fraction(0, 1))
        self.assertEqual(t45, Fraction(100_000_000, 100_000_000))
        self.assertEqual(t_neg45, Fraction(-100_000_000, 100_000_000))

    def test_trigonometria_retorna_estritamente_fraction(self):
        for ang in range(-90, 91, 15):
            s = obter_seno_graus_racional(ang)
            c = obter_cosseno_graus_racional(ang)
            t = obter_tangente_graus_racional(ang)
            self.assertIsInstance(s, Fraction)
            self.assertIsInstance(c, Fraction)
            self.assertIsInstance(t, Fraction)


if __name__ == "__main__":
    unittest.main()
