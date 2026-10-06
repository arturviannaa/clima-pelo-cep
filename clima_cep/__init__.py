"""Clima pelo CEP: consulta o endereço no ViaCEP e a previsão do tempo no Open-Meteo."""

from .exceptions import (
    ApiExternaError,
    CepInvalidoError,
    CepNaoEncontradoError,
    ClimaCepError,
    LocalizacaoNaoEncontradaError,
)
from .models import RelatorioClima
from .service import ClimaService, salvar_json, validar_cep

__all__ = [
    "ApiExternaError",
    "CepInvalidoError",
    "CepNaoEncontradoError",
    "ClimaCepError",
    "ClimaService",
    "LocalizacaoNaoEncontradaError",
    "RelatorioClima",
    "salvar_json",
    "validar_cep",
]
