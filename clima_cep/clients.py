"""Clientes HTTP das APIs externas (ViaCEP e Open-Meteo)."""

import unicodedata

import requests

from .exceptions import ApiExternaError, CepNaoEncontradoError, LocalizacaoNaoEncontradaError
from .models import (
    ClimaAtual,
    Coordenadas,
    Endereco,
    PrevisaoDia,
    PrevisaoHora,
    descrever_codigo_clima,
)

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


class OpenMeteoClient:
    """Geocodificação e previsão do tempo na API Open-Meteo (https://open-meteo.com)."""

    URL_GEOCODING = "https://geocoding-api.open-meteo.com/v1/search"
    URL_PREVISAO = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def buscar_coordenadas(self, cidade: str, estado: str) -> Coordenadas:
        """Encontra latitude/longitude da cidade, desempatando pelo estado (há cidades homônimas)."""
        params = {"name": cidade, "count": 10, "language": "pt", "countryCode": "BR", "format": "json"}
        dados = requisitar_json(self.session, self.URL_GEOCODING, "API de Geocoding do Open-Meteo", params)

        resultados = dados.get("results") or []
        candidatos = [r for r in resultados if normalizar(r.get("name", "")) == normalizar(cidade)]
        if estado:
            candidatos = [r for r in candidatos if normalizar(r.get("admin1", "")) == normalizar(estado)]

        if not candidatos:
            raise LocalizacaoNaoEncontradaError(f"Não foi possível localizar as coordenadas de {cidade}.")

        melhor = candidatos[0]
        return Coordenadas(
            latitude=melhor["latitude"],
            longitude=melhor["longitude"],
            fuso_horario=melhor.get("timezone", "America/Sao_Paulo"),
        )

    def buscar_previsao(
        self, coordenadas: Coordenadas, dias: int = 7, horas: int = 48
    ) -> tuple[ClimaAtual, list[PrevisaoHora], list[PrevisaoDia]]:
        """Busca clima atual, previsão horária e previsão diária em uma única requisição."""
        params = {
            "latitude": coordenadas.latitude,
            "longitude": coordenadas.longitude,
            "timezone": coordenadas.fuso_horario,
            "forecast_days": dias,
            "forecast_hours": horas,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
            "wind_speed_10m,weather_code,is_day",
            "hourly": "temperature_2m,precipitation_probability",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_sum,precipitation_probability_max",
        }
        dados = requisitar_json(self.session, self.URL_PREVISAO, "API de Previsão do Open-Meteo", params)

        try:
            return (
                self._montar_atual(dados["current"]),
                self._montar_horas(dados["hourly"]),
                self._montar_dias(dados["daily"]),
            )
        except (KeyError, IndexError, TypeError) as erro:
            raise ApiExternaError(f"Resposta do Open-Meteo em formato inesperado: {erro!r}") from erro

    # O Open-Meteo devolve "current" como objeto, mas "hourly" e "daily" como
    # listas paralelas (uma lista por variável, todas indexadas pela lista "time").

    @staticmethod
    def _montar_atual(atual: dict) -> ClimaAtual:
        return ClimaAtual(
            horario=atual["time"],
            temperatura=atual["temperature_2m"],
            sensacao_termica=atual["apparent_temperature"],
            umidade=atual["relative_humidity_2m"],
            vento_kmh=atual["wind_speed_10m"],
            codigo_clima=atual["weather_code"],
            descricao=descrever_codigo_clima(atual["weather_code"]),
            dia=bool(atual["is_day"]),
        )

    @staticmethod
    def _montar_horas(horaria: dict) -> list[PrevisaoHora]:
        return [
            PrevisaoHora(
                horario=horario,
                temperatura=horaria["temperature_2m"][i],
                chance_chuva=horaria["precipitation_probability"][i],
            )
            for i, horario in enumerate(horaria["time"])
        ]

    @staticmethod
    def _montar_dias(diaria: dict) -> list[PrevisaoDia]:
        return [
            PrevisaoDia(
                data=data,
                temperatura_min=diaria["temperature_2m_min"][i],
                temperatura_max=diaria["temperature_2m_max"][i],
                chuva_mm=diaria["precipitation_sum"][i],
                chance_chuva=diaria["precipitation_probability_max"][i],
                codigo_clima=diaria["weather_code"][i],
                descricao=descrever_codigo_clima(diaria["weather_code"][i]),
            )
            for i, data in enumerate(diaria["time"])
        ]
