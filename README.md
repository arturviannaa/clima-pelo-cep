# 🌦️ Clima pelo CEP

**Checkpoint 5 – Computational Thinking With Python (FIAP)**

| Integrante | RM |
|---|---|
| Artur Figueiredo Vianna | RM571866 |
| Cassiano Rocha Assumpção | RM568632 |
| Pedro Perraro John | RM573068 |

---

## 1. Problema

Quase todo serviço de previsão do tempo pede o **nome da cidade** ou **coordenadas geográficas**. No dia a dia, porém, o dado que as pessoas e os sistemas têm em mãos é o **CEP**: no cadastro de um cliente, no endereço de entrega, no formulário de um app.

Exemplos de quem precisa dessa informação:
- uma transportadora que quer saber se vai chover no destino das entregas da semana;
- um app de eventos ao ar livre que avisa o participante sobre o clima do local;
- qualquer pessoa que quer a previsão "de casa" sem saber a latitude e a longitude.

**A aplicação recebe um CEP e devolve o endereço, o clima atual e a previsão para os próximos dias**, de três formas:

1. uma **API REST própria** (FastAPI), documentada em **OpenAPI**;
2. um **dashboard interativo** (Streamlit) com métricas, gráficos e tabela;
3. um **script** que consulta vários CEPs e salva os resultados em **JSON**.

## 2. APIs externas utilizadas

Todas são **públicas, gratuitas e não exigem chave de acesso**, o que as torna adequadas para uso acadêmico.

| API | Para que usamos | Documentação |
|---|---|---|
| **ViaCEP** | CEP → endereço (rua, bairro, cidade, UF, estado) | https://viacep.com.br |
| **Open-Meteo Geocoding** | nome da cidade → latitude/longitude | https://open-meteo.com/en/docs/geocoding-api |
| **Open-Meteo Forecast** | latitude/longitude → clima atual e previsão | https://open-meteo.com/en/docs |

### Fluxo de dados

```
           ┌──────────┐   cidade + estado   ┌──────────────────────┐   lat/lon   ┌──────────────────────┐
  CEP ───► │  ViaCEP  │ ──────────────────► │ Open-Meteo Geocoding │ ──────────► │ Open-Meteo Forecast  │ ───► Relatório
           └──────────┘                     └──────────────────────┘             └──────────────────────┘
```

O ViaCEP **não fornece coordenadas**. Por isso há um passo intermediário de geocodificação, e a previsão é feita **no nível da cidade** do CEP.

### 2.1 ViaCEP: estrutura da resposta

`GET https://viacep.com.br/ws/01310100/json/` (resposta completa em [`dados/respostas_brutas/viacep.json`](dados/respostas_brutas/viacep.json))

```json
{
  "cep": "01310-100",
  "logradouro": "Avenida Paulista",
  "bairro": "Bela Vista",
  "localidade": "São Paulo",
  "uf": "SP",
  "estado": "São Paulo",
  "ibge": "3550308",
  "ddd": "11"
}
```

| Campo | Uso no projeto |
|---|---|
| `localidade` | nome da cidade, enviado para a geocodificação |
| `estado` | nome completo do estado, usado para **desempatar cidades homônimas** (ex.: existe "São José" em SC, SP, RS…) |
| `logradouro`, `bairro`, `uf`, `cep` | exibidos no dashboard e no relatório |

**Comportamentos importantes, descobertos testando a API:**
- Um **CEP inexistente** com formato válido retorna **HTTP 200** com o corpo `{"erro": "true"}`, em vez de 404 ([`viacep_cep_inexistente.json`](dados/respostas_brutas/viacep_cep_inexistente.json)). O código verifica esse campo explicitamente.
- Um **CEP com formato inválido** (ex.: `123`) retorna **HTTP 400 com HTML**, não JSON. Por isso validamos o formato **antes** de chamar a API.

### 2.2 Open-Meteo Geocoding: estrutura da resposta

`GET https://geocoding-api.open-meteo.com/v1/search?name=São Paulo&countryCode=BR&language=pt` (completa em [`open_meteo_geocoding.json`](dados/respostas_brutas/open_meteo_geocoding.json))

```json
{
  "results": [
    { "name": "São Paulo", "latitude": -23.5475, "longitude": -46.63611,
      "admin1": "São Paulo", "timezone": "America/Sao_Paulo", "country_code": "BR" }
  ]
}
```

A API devolve **uma lista de candidatos**. Escolhemos aquele cujo `name` é igual à cidade **e** cujo `admin1` (estado) é igual ao `estado` do ViaCEP, ignorando acentos e maiúsculas. Se nada for encontrado, a chave `results` **nem aparece** na resposta, e o código trata esse caso.

### 2.3 Open-Meteo Forecast: estrutura da resposta

`GET https://api.open-meteo.com/v1/forecast?latitude=...&longitude=...&current=...&hourly=...&daily=...` (completa em [`open_meteo_previsao.json`](dados/respostas_brutas/open_meteo_previsao.json))

A resposta tem **dois formatos diferentes** dentro do mesmo JSON:

```json
{
  "current": { "time": "2026-10-06T19:15", "temperature_2m": 19.5, "weather_code": 51, "is_day": 0 },
  "hourly": {
    "time":                      ["2026-10-06T19:00", "2026-10-06T20:00", "..."],
    "temperature_2m":            [19.5, 19.4, "..."],
    "precipitation_probability": [99, 100, "..."]
  },
  "daily": {
    "time":               ["2026-10-06", "2026-10-07", "..."],
    "temperature_2m_max": [23.6, 26.6, "..."],
    "weather_code":       [95, 55, "..."]
  }
}
```

- `current` é um **objeto simples**: um valor por variável.
- `hourly` e `daily` são **listas paralelas**: cada variável é uma lista, e o índice `i` de todas elas corresponde a `time[i]`. O código percorre `time` com `enumerate` e monta um objeto por hora ou por dia (`OpenMeteoClient._montar_horas` / `_montar_dias`).
- `weather_code` é um **código numérico WMO** (ex.: `0` = céu limpo, `61` = chuva leve, `95` = trovoada), traduzido para português pela função `descrever_codigo_clima()`.
- As variáveis retornadas são **escolhidas na requisição** pelos parâmetros `current`, `hourly` e `daily`. Pedimos só o que usamos.

## 3. Nossa API (OpenAPI)

A API própria foi feita com **FastAPI**, que gera a especificação **OpenAPI 3.1** automaticamente.

- 📄 **Especificação OpenAPI:** [`docs/openapi.json`](docs/openapi.json) (pode ser aberta em https://editor.swagger.io)
- 🧪 **Swagger UI interativo:** http://127.0.0.1:8000/docs (com a API rodando)
- 📘 **ReDoc:** http://127.0.0.1:8000/redoc

| Método | Rota | Descrição | Respostas |
|---|---|---|---|
| GET | `/saude` | Verifica se a API está no ar | 200 |
| GET | `/endereco/{cep}` | Apenas o endereço do CEP | 200, 404, 422, 502 |
| GET | `/clima/{cep}?dias=7&horas=48` | Endereço + clima atual + previsão horária e diária | 200, 404, 422, 502 |

Exemplo de erro:
```json
// GET /clima/99999999  →  404
{ "erro": "CepNaoEncontradoError", "detalhe": "O CEP 99999999 não foi encontrado." }
```

## 4. Como executar

Requisitos: **Python 3.10+** e acesso à internet.

```bash
# 1. Criar e ativar um ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Instalar as dependências
pip install -r requirements.txt

# 3a. Dashboard (abre em http://localhost:8501)
streamlit run dashboard.py

# 3b. API REST (abre em http://127.0.0.1:8000/docs)
python api.py

# 3c. Gerar o arquivo JSON com dados da API
python exportar_json.py                        # CEPs de exemplo
python exportar_json.py 01310-100 20040-020    # CEPs à escolha

# (opcional) Regerar a especificação OpenAPI
python api.py --openapi
```

## 5. Arquivos JSON com dados obtidos das APIs

| Arquivo | Conteúdo |
|---|---|
| [`dados/clima_2026-10-06.json`](dados/clima_2026-10-06.json) | Resultado do `exportar_json.py` para 5 capitais (SP, RJ, DF, BA, RS): endereço, coordenadas, clima atual, 48h e 7 dias de previsão |
| [`dados/respostas_brutas/`](dados/respostas_brutas/) | Respostas **originais**, sem tratamento, de cada API, para comparar com o formato que a aplicação produz |
| [`docs/openapi.json`](docs/openapi.json) | Especificação OpenAPI da nossa API |

O dashboard também tem um botão **"Baixar dados em JSON"** para cada consulta.

## 6. Estrutura do projeto

```
├── clima_cep/            # núcleo da aplicação (pacote Python)
│   ├── exceptions.py     # hierarquia de exceções
│   ├── models.py         # dataclasses + tradução dos códigos WMO
│   ├── clients.py        # ViaCepClient e OpenMeteoClient (requisições HTTP)
│   └── service.py        # ClimaService (orquestra o fluxo) + validar_cep / salvar_json
├── api.py                # API REST (FastAPI) → OpenAPI
├── dashboard.py          # Dashboard (Streamlit)
├── exportar_json.py      # Script de exportação para JSON
├── dados/                # JSONs obtidos das APIs
├── docs/openapi.json     # Especificação da nossa API
└── requirements.txt
```

A API, o dashboard e o script **reutilizam o mesmo núcleo** (`clima_cep`). Cada interface só cuida de apresentar os dados.

### Orientação a objetos

| Classe | Responsabilidade |
|---|---|
| `ViaCepClient`, `OpenMeteoClient` | Uma classe por API externa. Encapsula URL, parâmetros e conversão da resposta |
| `ClimaService` | Orquestra o fluxo CEP → endereço → coordenadas → previsão |
| `Endereco`, `Coordenadas`, `ClimaAtual`, `PrevisaoHora`, `PrevisaoDia`, `RelatorioClima` | `dataclasses` que transformam o JSON cru em objetos tipados (ex.: `Endereco.from_viacep()`) |
| `ClimaCepError` e subclasses | Exceções próprias, cada uma com o status HTTP correspondente |

Funções auxiliares: `validar_cep()`, `requisitar_json()`, `normalizar()`, `descrever_codigo_clima()`, `salvar_json()`.

## 7. Tratamento de erros

Toda requisição passa por `requisitar_json()` ([`clima_cep/clients.py`](clima_cep/clients.py)), que usa `timeout` e converte as exceções da biblioteca `requests` em exceções da aplicação:

| Situação | Exceção | HTTP na nossa API | Mensagem no dashboard |
|---|---|---|---|
| CEP com formato inválido (`123`, `abcde-fgh`) | `CepInvalidoError` | 422 | ✏️ aviso |
| CEP inexistente (`{"erro": "true"}` do ViaCEP) | `CepNaoEncontradoError` | 404 | 🔎 aviso |
| Cidade sem coordenadas no geocoding | `LocalizacaoNaoEncontradaError` | 404 | 🗺️ erro |
| Timeout (> 10 s) | `ApiExternaError` | 502 | 🌐 erro |
| Sem internet / falha de conexão | `ApiExternaError` | 502 | 🌐 erro |
| API externa responde 4xx/5xx | `ApiExternaError` | 502 | 🌐 erro |
| Resposta não é JSON válido | `ApiExternaError` | 502 | 🌐 erro |
| JSON sem um campo esperado (`KeyError`, `IndexError`) | `ApiExternaError` | 502 | 🌐 erro |
| Falha ao gravar o arquivo JSON | `RuntimeError` | — | — |

No `exportar_json.py`, um CEP com erro **não interrompe** os demais: a falha é registrada na chave `"falhas"` do JSON gerado.

## 8. Limitações conhecidas

- A previsão é por **cidade**, não por rua, porque o ViaCEP não retorna coordenadas.
- Depende da disponibilidade das APIs públicas. O dashboard guarda cada consulta em cache por 10 minutos para reduzir requisições repetidas.
