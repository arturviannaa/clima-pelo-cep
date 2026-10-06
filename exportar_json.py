"""Consulta o clima de um ou mais CEPs e salva o resultado em dados/.

Uso:
    python exportar_json.py                       # CEPs de exemplo
    python exportar_json.py 01310-100 20040-020   # CEPs escolhidos
"""

import sys
from datetime import date

from clima_cep import ClimaCepError, ClimaService, salvar_json

CEPS_EXEMPLO = [
    "01310-100",  # Av. Paulista - São Paulo/SP
    "20040-020",  # Centro - Rio de Janeiro/RJ
    "70040-010",  # Esplanada - Brasília/DF
    "40015-970",  # Comércio - Salvador/BA
    "90010-150",  # Centro Histórico - Porto Alegre/RS
]


def exportar(ceps: list[str]) -> int:
    servico = ClimaService()
    relatorios, falhas = [], []

    for cep in ceps:
        try:
            relatorio = servico.consultar(cep)
        except ClimaCepError as erro:
            print(f"[ERRO] {cep}: {erro.mensagem}")
            falhas.append({"cep": cep, "erro": type(erro).__name__, "detalhe": erro.mensagem})
            continue

        relatorios.append(relatorio.to_dict())
        atual = relatorio.atual
        print(f"[OK]   {cep}: {relatorio.endereco.resumo()} - {atual.temperatura}°C, {atual.descricao}")

    if not relatorios:
        print("Nenhuma consulta funcionou; nada foi salvo.")
        return 1

    caminho = salvar_json({"consultas": relatorios, "falhas": falhas}, f"dados/clima_{date.today()}.json")
    print(f"\n{len(relatorios)} consulta(s) salva(s) em {caminho}")
    return 0


if __name__ == "__main__":
    sys.exit(exportar(sys.argv[1:] or CEPS_EXEMPLO))
