"""Codecs e serializadores canônicos determinísticos para estabilidade de taludes NBR 11682.

LOFRANO TECNOLOGIA.
Rejeita estritamente BOM, floats, chaves duplicadas e profundidade excessiva.
"""

from fractions import Fraction
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from .domain import (
    CirculoRuptura,
    Ponto2D,
    PropriedadesSolo,
    ResultadoEstabilidade,
    TaludeInput,
    formatar_comprimento_m,
    formatar_forca_kn,
    formatar_fracao_decimal,
    formatar_pressao_kpa,
)
from .errors import (
    ErroCodec,
    ERR_BOM_DETECTADO,
    ERR_CHAVE_DUPLICADA,
    ERR_FLOAT_PROIBIDO,
    ERR_PROFUNDIDADE_EXCEDIDA,
    ERR_VALIDACAO_DOMINIO,
)

LIMITE_PROFUNDIDADE_MAXIMA = 32


def _verificar_profundidade(obj: Any, nivel: int = 0) -> None:
    if nivel > LIMITE_PROFUNDIDADE_MAXIMA:
        raise ErroCodec(
            f"Profundidade de aninhamento excedeu o limite máximo de {LIMITE_PROFUNDIDADE_MAXIMA}.",
            ERR_PROFUNDIDADE_EXCEDIDA,
        )
    if isinstance(obj, dict):
        for v in obj.values():
            _verificar_profundidade(v, nivel + 1)
    elif isinstance(obj, list):
        for item in obj:
            _verificar_profundidade(item, nivel + 1)


def _verificar_sem_float(obj: Any) -> None:
    if isinstance(obj, float):
        raise ErroCodec("Números em ponto flutuante (float) são terminantemente proibidos.", ERR_FLOAT_PROIBIDO)
    if isinstance(obj, dict):
        for k, v in obj.items():
            _verificar_sem_float(k)
            _verificar_sem_float(v)
    elif isinstance(obj, list):
        for item in obj:
            _verificar_sem_float(item)


def decodificar_json_canonico(conteudo: Union[str, bytes]) -> Any:
    """Decodifica JSON rejeitando BOM, floats, chaves duplicadas e profundidade excessiva."""
    if isinstance(conteudo, bytes):
        if conteudo.startswith(b"\xef\xbb\xbf"):
            raise ErroCodec("Byte Order Mark (BOM) UTF-8 detectado e proibido.", ERR_BOM_DETECTADO)
        texto = conteudo.decode("utf-8")
    else:
        if conteudo.startswith("\ufeff"):
            raise ErroCodec("Byte Order Mark (BOM) UTF-8 detectado e proibido.", ERR_BOM_DETECTADO)
        texto = conteudo

    def pares_sem_duplicatas(pares: List[Tuple[str, Any]]) -> Dict[str, Any]:
        dicionario: Dict[str, Any] = {}
        for chave, valor in pares:
            if chave in dicionario:
                raise ErroCodec(f"Chave duplicada detectada no JSON: '{chave}'.", ERR_CHAVE_DUPLICADA)
            dicionario[chave] = valor
        return dicionario

    def rejeitar_float(token: str) -> None:
        raise ErroCodec(
            f"Número em ponto flutuante (float) detectado no JSON: '{token}'. "
            "Use apenas grandezas inteiras (milímetros, Pascals, N/m³, graus inteiros).",
            ERR_FLOAT_PROIBIDO,
        )

    try:
        obj = json.loads(
            texto,
            object_pairs_hook=pares_sem_duplicatas,
            parse_float=rejeitar_float,
        )
    except json.JSONDecodeError as e:
        raise ErroCodec(f"Falha de sintaxe no JSON: {e}", "ERR_JSON_SINTAXE")

    _verificar_profundidade(obj)
    _verificar_sem_float(obj)
    return obj


def serializar_json_canonico(dados: Any) -> str:
    """Serializa estruturas de dados em JSON canônico estrito e determinístico."""
    _verificar_profundidade(dados)
    _verificar_sem_float(dados)

    return json.dumps(
        dados,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def carregar_talude(caminho: Union[str, Path]) -> TaludeInput:
    """Lê arquivo JSON e instancia o modelo de estabilidade de talude."""
    p = Path(caminho)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo de talude não encontrado: '{p}'")

    dados = decodificar_json_canonico(p.read_bytes())
    if not isinstance(dados, dict):
        raise ErroCodec("O arquivo deve conter um objeto JSON na raiz.", ERR_VALIDACAO_DOMINIO)

    campos_obrigatorios = [
        "nome_talude",
        "descricao",
        "nivel_seguranca_nbr11682",
        "perfil_terreno",
        "circulo_tentativa",
        "solo",
    ]
    for campo in campos_obrigatorios:
        if campo not in dados:
            raise ErroCodec(f"Campo obrigatório ausente no JSON: '{campo}'.", ERR_VALIDACAO_DOMINIO)

    pontos_perfil: List[Ponto2D] = []
    for pt in dados["perfil_terreno"]:
        pontos_perfil.append(Ponto2D(x_mm=pt["x_mm"], y_mm=pt["y_mm"]))

    circ_raw = dados["circulo_tentativa"]
    circulo = CirculoRuptura(
        centro_x_mm=circ_raw["centro_x_mm"],
        centro_y_mm=circ_raw["centro_y_mm"],
        raio_mm=circ_raw["raio_mm"],
    )

    solo_raw = dados["solo"]
    solo = PropriedadesSolo(
        nome_camada=solo_raw["nome_camada"],
        peso_especifico_n_m3=solo_raw["peso_especifico_n_m3"],
        coesao_efetiva_pa=solo_raw["coesao_efetiva_pa"],
        angulo_atrito_graus=solo_raw["angulo_atrito_graus"],
    )

    return TaludeInput(
        nome_talude=dados["nome_talude"],
        descricao=dados["descricao"],
        nivel_seguranca_nbr11682=dados["nivel_seguranca_nbr11682"],
        perfil_terreno=pontos_perfil,
        circulo_tentativa=circulo,
        solo=solo,
        numero_fatias=dados.get("numero_fatias", 10),
        nivel_dagua_y_mm=dados.get("nivel_dagua_y_mm"),
        sobrecarga_crista_pa=dados.get("sobrecarga_crista_pa", 0),
    )


def decodificar_talude_json_str(conteudo: Union[str, bytes]) -> TaludeInput:
    """Decodifica string ou bytes JSON e instancia o modelo TaludeInput."""
    dados = decodificar_json_canonico(conteudo)
    if not isinstance(dados, dict):
        raise ErroCodec("O JSON deve conter um objeto na raiz.", ERR_VALIDACAO_DOMINIO)

    campos_obrigatorios = [
        "nome_talude",
        "descricao",
        "nivel_seguranca_nbr11682",
        "perfil_terreno",
        "circulo_tentativa",
        "solo",
    ]
    for campo in campos_obrigatorios:
        if campo not in dados:
            raise ErroCodec(f"Campo obrigatório ausente no JSON: '{campo}'.", ERR_VALIDACAO_DOMINIO)

    pontos_perfil: List[Ponto2D] = []
    for pt in dados["perfil_terreno"]:
        pontos_perfil.append(Ponto2D(x_mm=pt["x_mm"], y_mm=pt["y_mm"]))

    circ_raw = dados["circulo_tentativa"]
    circulo = CirculoRuptura(
        centro_x_mm=circ_raw["centro_x_mm"],
        centro_y_mm=circ_raw["centro_y_mm"],
        raio_mm=circ_raw["raio_mm"],
    )

    solo_raw = dados["solo"]
    solo = PropriedadesSolo(
        nome_camada=solo_raw["nome_camada"],
        peso_especifico_n_m3=solo_raw["peso_especifico_n_m3"],
        coesao_efetiva_pa=solo_raw["coesao_efetiva_pa"],
        angulo_atrito_graus=solo_raw["angulo_atrito_graus"],
    )

    return TaludeInput(
        nome_talude=dados["nome_talude"],
        descricao=dados["descricao"],
        nivel_seguranca_nbr11682=dados["nivel_seguranca_nbr11682"],
        perfil_terreno=pontos_perfil,
        circulo_tentativa=circulo,
        solo=solo,
        numero_fatias=dados.get("numero_fatias", 10),
        nivel_dagua_y_mm=dados.get("nivel_dagua_y_mm"),
        sobrecarga_crista_pa=dados.get("sobrecarga_crista_pa", 0),
    )


def talude_para_dict(projeto: TaludeInput) -> Dict[str, Any]:
    """Converte o objeto TaludeInput para dicionário canônico determinístico."""
    d: Dict[str, Any] = {
        "nome_talude": projeto.nome_talude,
        "descricao": projeto.descricao,
        "nivel_seguranca_nbr11682": projeto.nivel_seguranca_nbr11682,
        "perfil_terreno": [{"x_mm": p.x_mm, "y_mm": p.y_mm} for p in projeto.perfil_terreno],
        "circulo_tentativa": {
            "centro_x_mm": projeto.circulo_tentativa.centro_x_mm,
            "centro_y_mm": projeto.circulo_tentativa.centro_y_mm,
            "raio_mm": projeto.circulo_tentativa.raio_mm,
        },
        "solo": {
            "nome_camada": projeto.solo.nome_camada,
            "peso_especifico_n_m3": projeto.solo.peso_especifico_n_m3,
            "coesao_efetiva_pa": projeto.solo.coesao_efetiva_pa,
            "angulo_atrito_graus": projeto.solo.angulo_atrito_graus,
        },
        "numero_fatias": projeto.numero_fatias,
        "sobrecarga_crista_pa": projeto.sobrecarga_crista_pa,
    }
    if projeto.nivel_dagua_y_mm is not None:
        d["nivel_dagua_y_mm"] = projeto.nivel_dagua_y_mm
    return d


def codificar_talude_json_str(projeto: TaludeInput) -> str:
    """Serializa modelo TaludeInput em string JSON canônica."""
    return serializar_json_canonico(talude_para_dict(projeto))


def codificar_resultado_json_str(resultado: ResultadoEstabilidade) -> str:
    """Serializa resultado da estabilidade em string JSON canônica."""
    return serializar_json_canonico(resultado_para_dict(resultado))


def resultado_para_dict(resultado: ResultadoEstabilidade) -> Dict[str, Any]:
    """Converte o resultado do cálculo para dicionário canônico determinístico."""
    fatias_json = []
    for f in resultado.fatias:
        fatias_json.append({
            "indice": f.indice,
            "x_central_mm": f.x_central_mm,
            "x_central_formatado": formatar_comprimento_m(f.x_central_mm),
            "largura_mm": f.largura_mm,
            "largura_formatada": formatar_comprimento_m(f.largura_mm),
            "y_topo_mm": f.y_topo_mm,
            "y_topo_formatado": formatar_comprimento_m(f.y_topo_mm),
            "y_base_mm": f.y_base_mm,
            "y_base_formatado": formatar_comprimento_m(f.y_base_mm),
            "altura_media_mm": f.altura_media_mm,
            "altura_media_formatada": formatar_comprimento_m(f.altura_media_mm),
            "inclinacao_base_graus": f.inclinacao_base_graus,
            "peso_fatia_n": f.peso_fatia_n,
            "peso_fatia_formatado": formatar_forca_kn(f.peso_fatia_n),
            "poropressao_base_pa": f.poropressao_base_pa,
            "poropressao_base_formatada": formatar_pressao_kpa(f.poropressao_base_pa),
            "forca_atuante_tangencial_n": f.forca_atuante_tangencial_n,
            "forca_atuante_formatada": formatar_forca_kn(f.forca_atuante_tangencial_n),
            "forca_resistente_fellenius_n": f.forca_resistente_fellenius_n,
            "forca_resistente_fellenius_formatada": formatar_forca_kn(f.forca_resistente_fellenius_n),
        })

    return {
        "talude": {
            "nome": resultado.nome_talude,
            "descricao": resultado.descricao,
            "nivel_seguranca_nbr11682": resultado.nivel_seguranca,
        },
        "fatores_de_seguranca": {
            "fs_minimo_exigido_numerador": resultado.fs_minimo_exigido.numerator,
            "fs_minimo_exigido_denominador": resultado.fs_minimo_exigido.denominator,
            "fs_minimo_exigido_formatado": formatar_fracao_decimal(resultado.fs_minimo_exigido),
            "fator_seguranca_fellenius_numerador": resultado.fator_seguranca_fellenius.numerator,
            "fator_seguranca_fellenius_denominador": resultado.fator_seguranca_fellenius.denominator,
            "fator_seguranca_fellenius_formatado": formatar_fracao_decimal(resultado.fator_seguranca_fellenius),
            "fator_seguranca_bishop_numerador": resultado.fator_seguranca_bishop.numerator,
            "fator_seguranca_bishop_denominador": resultado.fator_seguranca_bishop.denominator,
            "fator_seguranca_bishop_formatado": formatar_fracao_decimal(resultado.fator_seguranca_bishop),
            "conforme_nbr11682": resultado.conforme_nbr11682,
            "diagnostico": resultado.diagnostico,
            "iteracoes_bishop": resultado.iteracoes_bishop,
        },
        "esforcos_globais": {
            "peso_total_maciço_n": resultado.peso_total_maciço_n,
            "peso_total_formatado": formatar_forca_kn(resultado.peso_total_maciço_n),
            "momento_atuante_total_nm": resultado.momento_atuante_total_nm,
            "momento_resistente_fellenius_nm": resultado.momento_resistente_fellenius_nm,
            "momento_resistente_bishop_nm": resultado.momento_resistente_bishop_nm,
        },
        "fatias": fatias_json,
    }
