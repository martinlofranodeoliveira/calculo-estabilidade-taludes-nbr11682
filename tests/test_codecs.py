"""Testes unitários dos codecs canônicos JSON determinísticos (NBR 11682).

LOFRANO TECNOLOGIA.
"""

from fractions import Fraction
import json
import unittest

from estabilidade_taludes.codecs import (
    codificar_resultado_json_str,
    codificar_talude_json_str,
    decodificar_json_canonico,
    decodificar_talude_json_str,
    serializar_json_canonico,
)
from estabilidade_taludes.domain import (
    CirculoRuptura,
    Ponto2D,
    PropriedadesSolo,
    ResultadoEstabilidade,
    TaludeInput,
)
from estabilidade_taludes.errors import ErroCodec


class TestCodecsCanonicos(unittest.TestCase):
    """Validação de segurança dos codecs JSON (rejeição de BOM, floats, chaves duplicadas)."""

    def test_rejeicao_bom(self):
        json_com_bom = b"\xef\xbb\xbf{\"nome\": \"teste\"}"
        with self.assertRaises(ErroCodec):
            decodificar_json_canonico(json_com_bom)

        json_str_bom = "\ufeff{\"nome\": \"teste\"}"
        with self.assertRaises(ErroCodec):
            decodificar_json_canonico(json_str_bom)

    def test_rejeicao_float(self):
        json_float = '{"peso_especifico_n_m3": 18.5}'
        with self.assertRaises(ErroCodec):
            decodificar_json_canonico(json_float)

    def test_rejeicao_chaves_duplicadas(self):
        json_dup = '{"nome": "Talude 1", "nome": "Talude 2"}'
        with self.assertRaises(ErroCodec):
            decodificar_json_canonico(json_dup)

    def test_rejeicao_profundidade_excessiva(self):
        d = {"chave": 1}
        for _ in range(35):
            d = {"sub": d}
        with self.assertRaises(ErroCodec):
            serializar_json_canonico(d)

    def test_roundtrip_talude_input(self):
        proj = TaludeInput(
            nome_talude="Corte Km 12",
            descricao="Solo residual",
            nivel_seguranca_nbr11682="MEDIO",
            perfil_terreno=[Ponto2D(0, 0), Ponto2D(10000, 5000), Ponto2D(20000, 5000)],
            circulo_tentativa=CirculoRuptura(10000, 15000, 12000),
            solo=PropriedadesSolo("Argila", 18000, 15000, 22),
            numero_fatias=10,
            nivel_dagua_y_mm=2000,
            sobrecarga_crista_pa=5000,
        )

        serializado = codificar_talude_json_str(proj)
        self.assertTrue(serializado.endswith("\n"))

        deserializado = decodificar_talude_json_str(serializado)
        self.assertEqual(deserializado.nome_talude, proj.nome_talude)
        self.assertEqual(deserializado.nivel_seguranca_nbr11682, "MEDIO")
        self.assertEqual(deserializado.perfil_terreno[1].x_mm, 10000)
        self.assertEqual(deserializado.circulo_tentativa.raio_mm, 12000)
        self.assertEqual(deserializado.solo.coesao_efetiva_pa, 15000)
        self.assertEqual(deserializado.nivel_dagua_y_mm, 2000)
        self.assertEqual(deserializado.sobrecarga_crista_pa, 5000)

    def test_codificar_resultado_json(self):
        res = ResultadoEstabilidade(
            nome_talude="Talude 1",
            descricao="Desc",
            nivel_seguranca="ALTO",
            fs_minimo_exigido=Fraction(3, 2),
            fator_seguranca_fellenius=Fraction(16, 10),
            fator_seguranca_bishop=Fraction(17, 10),
            peso_total_maciço_n=500000,
            momento_atuante_total_nm=10000000,
            momento_resistente_fellenius_nm=16000000,
            momento_resistente_bishop_nm=17000000,
            fatias=[],
            conforme_nbr11682=True,
            diagnostico="ESTÁVEL",
            iteracoes_bishop=4,
        )
        json_out = codificar_resultado_json_str(res)
        obj = json.loads(json_out)
        self.assertEqual(obj["talude"]["nome"], "Talude 1")
        self.assertEqual(obj["fatores_de_seguranca"]["fator_seguranca_bishop_formatado"], "1,700")
        self.assertTrue(obj["fatores_de_seguranca"]["conforme_nbr11682"])

    def test_json_sintaxe_invalida(self):
        with self.assertRaises(ErroCodec):
            decodificar_json_canonico("{chave: sem_aspas}")

    def test_talude_json_raiz_nao_objeto(self):
        with self.assertRaises(ErroCodec):
            decodificar_talude_json_str("[1, 2, 3]")

    def test_talude_json_campo_obrigatorio_ausente(self):
        with self.assertRaises(ErroCodec):
            decodificar_talude_json_str('{"nome_talude": "Incompleto"}')


if __name__ == "__main__":
    unittest.main()
