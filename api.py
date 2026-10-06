"""API REST própria (FastAPI). A documentação OpenAPI é gerada automaticamente em /docs.

Executar:      python api.py            (ou: uvicorn api:app --reload)
Exportar spec: python api.py --openapi  (gera docs/openapi.json)
"""

import argparse

from fastapi import FastAPI, Path, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from clima_cep import ClimaCepError, ClimaService, salvar_json, validar_cep
from clima_cep.models import Endereco, RelatorioClima

DESCRICAO = """
Consulta o **clima atual** e a **previsão do tempo** a partir de um **CEP brasileiro**.

Fluxo interno: CEP → [ViaCEP](https://viacep.com.br) (endereço) →
[Open-Meteo Geocoding](https://open-meteo.com/en/docs/geocoding-api) (latitude/longitude) →
[Open-Meteo Forecast](https://open-meteo.com/en/docs) (clima).

A previsão é feita no nível da **cidade** do CEP.
"""

app = FastAPI(
    title="Clima pelo CEP",
    description=DESCRICAO,
    version="1.0.0",
    contact={"name": "Checkpoint 5 - FIAP"},
)
servico = ClimaService()


class Erro(BaseModel):
    erro: str
    detalhe: str


RESPOSTAS_ERRO = {
    404: {"model": Erro, "description": "CEP ou localização não encontrados"},
    422: {"model": Erro, "description": "CEP ou parâmetro inválido"},
    502: {"model": Erro, "description": "Falha ao consultar uma API externa"},
}

CEP_PATH = Path(description="CEP com ou sem hífen", examples=["01310-100"])


@app.exception_handler(ClimaCepError)
async def tratar_erro_aplicacao(_: Request, erro: ClimaCepError) -> JSONResponse:
    """Converte as exceções da aplicação em respostas HTTP com o status adequado."""
    return JSONResponse(
        status_code=erro.status_http,
        content={"erro": type(erro).__name__, "detalhe": erro.mensagem},
    )


@app.get("/saude", tags=["Status"], summary="Verifica se a API está no ar")
def saude() -> dict:
    return {"status": "ok"}


@app.get(
    "/endereco/{cep}",
    response_model=Endereco,
    responses=RESPOSTAS_ERRO,
    tags=["Consultas"],
    summary="Endereço de um CEP",
)
def endereco(cep: str = CEP_PATH) -> Endereco:
    return servico.viacep.buscar_endereco(validar_cep(cep))


@app.get(
    "/clima/{cep}",
    response_model=RelatorioClima,
    responses=RESPOSTAS_ERRO,
    tags=["Consultas"],
    summary="Clima atual e previsão para um CEP",
)
def clima(
    cep: str = CEP_PATH,
    dias: int = Query(7, ge=1, le=16, description="Dias de previsão diária (1 a 16)"),
    horas: int = Query(48, ge=1, le=168, description="Horas de previsão horária (1 a 168)"),
) -> RelatorioClima:
    return servico.consultar(cep, dias=dias, horas=horas)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--openapi", action="store_true", help="apenas exporta docs/openapi.json")
    parser.add_argument("--porta", type=int, default=8000)
    args = parser.parse_args()

    if args.openapi:
        print(f"Especificação salva em {salvar_json(app.openapi(), 'docs/openapi.json')}")
    else:
        import uvicorn

        uvicorn.run(app, host="127.0.0.1", port=args.porta)
