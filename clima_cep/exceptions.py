"""Hierarquia de exceções da aplicação.

Todas herdam de ClimaCepError, então quem consome o serviço (API ou dashboard)
pode capturar um erro específico ou qualquer erro da aplicação de uma vez.
"""


class ClimaCepError(Exception):
    """Erro base da aplicação."""

    status_http = 500

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class CepInvalidoError(ClimaCepError):
    """O CEP informado não tem 8 dígitos numéricos."""

    status_http = 422


class CepNaoEncontradoError(ClimaCepError):
    """O CEP tem formato válido, mas não existe na base do ViaCEP."""

    status_http = 404


class LocalizacaoNaoEncontradaError(ClimaCepError):
    """Não foi possível obter as coordenadas da cidade do CEP."""

    status_http = 404


class ApiExternaError(ClimaCepError):
    """Falha ao consultar uma API externa (timeout, conexão, status HTTP ou JSON inválido)."""

    status_http = 502
