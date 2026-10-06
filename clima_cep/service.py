"""Regra de negócio: do CEP até o relatório de clima."""

import json
import re
from pathlib import Path

import requests

from .clients import OpenMeteoClient, ViaCepClient
from .exceptions import CepInvalidoError
from .models import RelatorioClima


def validar_cep(cep: str) -> str:
    """Aceita "01310-100", "01310100" ou " 01310 100 " e devolve só os 8 dígitos."""
    if not isinstance(cep, str):
        raise CepInvalidoError("O CEP deve ser informado como texto.")
    digitos = re.sub(r"[\s.-]", "", cep)
    if not re.fullmatch(r"\d{8}", digitos):
        raise CepInvalidoError(f"CEP inválido: '{cep}'. Informe 8 dígitos, ex.: 01310-100.")
    return digitos


def salvar_json(dados: dict | list, caminho: str | Path) -> Path:
    """Grava dados em um arquivo JSON legível (UTF-8, indentado)."""
    caminho = Path(caminho)
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, TypeError) as erro:
        raise RuntimeError(f"Não foi possível salvar o arquivo {caminho}: {erro}") from erro
    return caminho


class ClimaService:
    """Orquestra o fluxo CEP -> ViaCEP -> Geocoding -> Previsão."""

    def __init__(self, viacep: ViaCepClient | None = None, open_meteo: OpenMeteoClient | None = None):
        session = requests.Session()
        session.headers["User-Agent"] = "checkpoint5-clima-cep/1.0 (projeto academico FIAP)"
        self.viacep = viacep or ViaCepClient(session)
        self.open_meteo = open_meteo or OpenMeteoClient(session)

    def consultar(self, cep: str, dias: int = 7, horas: int = 48) -> RelatorioClima:
        cep_limpo = validar_cep(cep)
        endereco = self.viacep.buscar_endereco(cep_limpo)
        coordenadas = self.open_meteo.buscar_coordenadas(endereco.cidade, endereco.estado)
        atual, proximas_horas, proximos_dias = self.open_meteo.buscar_previsao(coordenadas, dias, horas)
        return RelatorioClima(
            endereco=endereco,
            coordenadas=coordenadas,
            atual=atual,
            proximas_horas=proximas_horas,
            proximos_dias=proximos_dias,
        )
