"""Clientes HTTP das APIs externas."""

import unicodedata

import requests

from .exceptions import ApiExternaError, CepNaoEncontradoError
from .models import Endereco

TIMEOUT_PADRAO = 10  # segundos


def requisitar_json(session: requests.Session, url: str, nome_api: str, params: dict | None = None) -> dict:
    """Faz um GET e devolve o corpo como dict, convertendo qualquer falha em ApiExternaError."""
    try:
        resposta = session.get(url, params=params, timeout=TIMEOUT_PADRAO)
        resposta.raise_for_status()
        return resposta.json()
    except requests.exceptions.Timeout as erro:
        raise ApiExternaError(f"{nome_api} demorou mais de {TIMEOUT_PADRAO}s para responder.") from erro
    except requests.exceptions.ConnectionError as erro:
        raise ApiExternaError(f"Não foi possível conectar à {nome_api}. Verifique sua internet.") from erro
    except requests.exceptions.HTTPError as erro:
        raise ApiExternaError(f"{nome_api} respondeu com erro HTTP {erro.response.status_code}.") from erro
    except requests.exceptions.JSONDecodeError as erro:
        raise ApiExternaError(f"{nome_api} retornou uma resposta que não é JSON válido.") from erro
    except requests.exceptions.RequestException as erro:
        raise ApiExternaError(f"Erro inesperado ao consultar a {nome_api}: {erro}") from erro


def normalizar(texto: str) -> str:
    """Remove acentos e caixa para comparar nomes ("São Paulo" == "sao paulo")."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.strip().lower()


class ViaCepClient:
    """Consulta endereços na API ViaCEP (https://viacep.com.br)."""

    URL_BASE = "https://viacep.com.br/ws"

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def buscar_endereco(self, cep: str) -> Endereco:
        """Recebe um CEP já validado (8 dígitos) e devolve o Endereco correspondente."""
        dados = requisitar_json(self.session, f"{self.URL_BASE}/{cep}/json/", "API ViaCEP")

        # Pegadinha do ViaCEP: um CEP inexistente volta com HTTP 200 e {"erro": "true"}
        # (string ou booleano, dependendo da versão), em vez de um 404.
        if str(dados.get("erro", "")).lower() == "true":
            raise CepNaoEncontradoError(f"O CEP {cep} não foi encontrado.")

        try:
            return Endereco.from_viacep(dados)
        except KeyError as erro:
            raise ApiExternaError(f"Resposta do ViaCEP sem o campo obrigatório {erro}.") from erro

