"""Módulo de tratamento de exceções e erros de estabilidade de taludes (NBR 11682).

LOFRANO TECNOLOGIA.
"""


class ErroEstabilidadeTaludes(Exception):
    """Exceção base para todas as falhas de cálculo de estabilidade de taludes."""

    def __init__(self, mensagem: str, codigo: str = "ERR_GENERICO"):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.codigo = codigo

    def __str__(self) -> str:
        return f"[{self.codigo}] {self.mensagem}"


class ErroValidacaoGeotecnica(ErroEstabilidadeTaludes):
    """Lançada quando a geometria do talude ou propriedades dos solos violam limites físicos."""

    def __init__(self, mensagem: str, codigo: str = "ERR_VALIDACAO"):
        super().__init__(mensagem, codigo)


class ErroGeometriaCirculo(ErroEstabilidadeTaludes):
    """Lançada quando o círculo de ruptura não intercepta o talude ou é geometricamente inconsistente."""

    def __init__(self, mensagem: str, codigo: str = "ERR_CIRCULO_INVALIDO"):
        super().__init__(mensagem, codigo)


class ErroConvergenciaBishop(ErroEstabilidadeTaludes):
    """Lançada quando o processo iterativo do método de Bishop Simplificado não converge."""

    def __init__(self, mensagem: str, codigo: str = "ERR_CONVERGENCIA_BISHOP"):
        super().__init__(mensagem, codigo)


class ErroCodec(ErroEstabilidadeTaludes):
    """Lançada quando a decodificação ou codificação canônica JSON falha."""

    def __init__(self, mensagem: str, codigo: str = "ERR_CODEC"):
        super().__init__(mensagem, codigo)


class ErroExportacao(ErroEstabilidadeTaludes):
    """Lançada quando a geração de relatórios, SVG, CSV ou ZIP falha."""

    def __init__(self, mensagem: str, codigo: str = "ERR_EXPORTACAO"):
        super().__init__(mensagem, codigo)


# Constantes de códigos de erro
ERR_VALIDACAO_DOMINIO = "ERR_VALIDACAO_DOMINIO"
ERR_FLOAT_PROIBIDO = "ERR_FLOAT_PROIBIDO"
ERR_BOM_DETECTADO = "ERR_BOM_DETECTADO"
ERR_CHAVE_DUPLICADA = "ERR_CHAVE_DUPLICADA"
ERR_PROFUNDIDADE_EXCEDIDA = "ERR_PROFUNDIDADE_EXCEDIDA"
ERR_FALHA_CONVERGENCIA = "ERR_FALHA_CONVERGENCIA"
ERR_RAIO_INSUFICIENTE = "ERR_RAIO_INSUFICIENTE"
ERR_CIRCULO_INVALIDO = "ERR_CIRCULO_INVALIDO"
ERR_ARQUIVO_EXISTENTE = "ERR_ARQUIVO_EXISTENTE"
ERR_ARQUIVO_ZIP = "ERR_ARQUIVO_ZIP"
ERR_GRAVACAO_ZIP = "ERR_GRAVACAO_ZIP"

# Alias para compatibilidade
ErroEstabilidadeTalude = ErroEstabilidadeTaludes

