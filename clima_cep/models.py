"""Modelos de dados: transformam o JSON cru das APIs em objetos tipados."""

from dataclasses import asdict, dataclass, field
from datetime import datetime

# Tabela de códigos WMO usada pelo Open-Meteo no campo "weather_code".
# Referência: https://open-meteo.com/en/docs (seção "WMO Weather interpretation codes")
CODIGOS_WMO = {
    0: "Céu limpo",
    1: "Predominantemente limpo",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Neblina",
    48: "Neblina com geada",
    51: "Garoa leve",
    53: "Garoa moderada",
    55: "Garoa intensa",
    56: "Garoa congelante leve",
    57: "Garoa congelante intensa",
    61: "Chuva leve",
    63: "Chuva moderada",
    65: "Chuva forte",
    66: "Chuva congelante leve",
    67: "Chuva congelante forte",
    71: "Neve leve",
    73: "Neve moderada",
    75: "Neve forte",
    77: "Grãos de neve",
    80: "Pancadas de chuva leves",
    81: "Pancadas de chuva moderadas",
    82: "Pancadas de chuva violentas",
    85: "Pancadas de neve leves",
    86: "Pancadas de neve fortes",
    95: "Trovoada",
    96: "Trovoada com granizo leve",
    99: "Trovoada com granizo forte",
}


def descrever_codigo_clima(codigo: int | None) -> str:
    """Converte um código WMO em uma descrição em português."""
    if codigo is None:
        return "Indisponível"
    return CODIGOS_WMO.get(codigo, f"Desconhecido (código {codigo})")


@dataclass
class Endereco:
    """Dados retornados pelo ViaCEP."""

    cep: str
    logradouro: str
    bairro: str
    cidade: str
    uf: str
    estado: str
    ibge: str

    @classmethod
    def from_viacep(cls, dados: dict) -> "Endereco":
        return cls(
            cep=dados.get("cep", ""),
            logradouro=dados.get("logradouro", ""),
            bairro=dados.get("bairro", ""),
            cidade=dados["localidade"],
            uf=dados["uf"],
            estado=dados.get("estado", ""),
            ibge=dados.get("ibge", ""),
        )

    def resumo(self) -> str:
        partes = [p for p in (self.logradouro, self.bairro) if p]
        partes.append(f"{self.cidade}/{self.uf}")
        return ", ".join(partes)


@dataclass
class Coordenadas:
    """Latitude/longitude obtidas pela Geocoding API do Open-Meteo."""

    latitude: float
    longitude: float
    fuso_horario: str


@dataclass
class ClimaAtual:
    horario: str
    temperatura: float
    sensacao_termica: float
    umidade: int
    vento_kmh: float
    codigo_clima: int
    descricao: str
    dia: bool


@dataclass
class PrevisaoHora:
    horario: str
    temperatura: float
    chance_chuva: int | None


@dataclass
class PrevisaoDia:
    data: str
    temperatura_min: float
    temperatura_max: float
    chuva_mm: float
    chance_chuva: int | None
    codigo_clima: int
    descricao: str


@dataclass
class RelatorioClima:
    """Resultado completo de uma consulta: endereço + clima atual + previsões."""

    endereco: Endereco
    coordenadas: Coordenadas
    atual: ClimaAtual
    proximas_horas: list[PrevisaoHora] = field(default_factory=list)
    proximos_dias: list[PrevisaoDia] = field(default_factory=list)
    consultado_em: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        return asdict(self)
