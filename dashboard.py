"""Dashboard Streamlit do Clima pelo CEP.

Executar: streamlit run dashboard.py
"""

import json

import pandas as pd
import streamlit as st

from clima_cep import (
    ApiExternaError,
    CepInvalidoError,
    CepNaoEncontradoError,
    ClimaService,
    LocalizacaoNaoEncontradaError,
)

st.set_page_config(page_title="Clima pelo CEP", page_icon="🌦️", layout="wide")


@st.cache_resource
def obter_servico() -> ClimaService:
    return ClimaService()


@st.cache_data(ttl=600, show_spinner=False)
def consultar_clima(cep: str, dias: int) -> dict:
    """Cacheia por 10 minutos para não repetir requisições do mesmo CEP."""
    return obter_servico().consultar(cep, dias=dias).to_dict()


def montar_tabela_horas(relatorio: dict) -> pd.DataFrame:
    df = pd.DataFrame(relatorio["proximas_horas"])
    df["horario"] = pd.to_datetime(df["horario"])
    return df.set_index("horario")


def montar_tabela_dias(relatorio: dict) -> pd.DataFrame:
    df = pd.DataFrame(relatorio["proximos_dias"])
    df["data"] = pd.to_datetime(df["data"]).dt.strftime("%a %d/%m")
    return df


def exibir_relatorio(relatorio: dict) -> None:
    endereco, atual = relatorio["endereco"], relatorio["atual"]

    linha_rua = ", ".join(p for p in (endereco["logradouro"], endereco["bairro"]) if p)
    st.subheader(f"📍 {endereco['cidade']} / {endereco['uf']}")
    st.caption(
        f"{linha_rua + ' · ' if linha_rua else ''}CEP {endereco['cep']} · "
        f"lat {relatorio['coordenadas']['latitude']:.3f}, lon {relatorio['coordenadas']['longitude']:.3f} · "
        f"atualizado em {atual['horario'].replace('T', ' ')}"
    )

    icone = "☀️" if atual["dia"] else "🌙"
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Temperatura", f"{atual['temperatura']:.1f} °C")
    col2.metric("Sensação térmica", f"{atual['sensacao_termica']:.1f} °C")
    col3.metric("Umidade", f"{atual['umidade']} %")
    col4.metric("Vento", f"{atual['vento_kmh']:.1f} km/h")
    col5.metric("Condição", f"{icone} {atual['descricao']}")

    horas = montar_tabela_horas(relatorio)
    dias = montar_tabela_dias(relatorio)

    graf1, graf2 = st.columns(2)
    with graf1:
        st.markdown(f"**Temperatura nas próximas {len(horas)} horas (°C)**")
        st.line_chart(horas[["temperatura"]], y_label="°C", x_label="")
    with graf2:
        st.markdown(f"**Chance de chuva nos próximos {len(dias)} dias (%)**")
        st.bar_chart(dias.set_index("data")[["chance_chuva"]], y_label="%", x_label="", sort=False)

    st.markdown("**Previsão diária**")
    st.dataframe(
        dias[["data", "descricao", "temperatura_min", "temperatura_max", "chance_chuva", "chuva_mm"]],
        hide_index=True,
        width="stretch",
        column_config={
            "data": "Dia",
            "descricao": "Condição",
            "temperatura_min": st.column_config.NumberColumn("Mín (°C)", format="%.1f"),
            "temperatura_max": st.column_config.NumberColumn("Máx (°C)", format="%.1f"),
            "chance_chuva": st.column_config.ProgressColumn("Chance de chuva", min_value=0, max_value=100, format="%d%%"),
            "chuva_mm": st.column_config.NumberColumn("Chuva (mm)", format="%.1f"),
        },
    )

    st.download_button(
        "⬇️ Baixar dados em JSON",
        data=json.dumps(relatorio, ensure_ascii=False, indent=2),
        file_name=f"clima_{endereco['cep']}.json",
        mime="application/json",
    )
    with st.expander("Ver JSON completo"):
        st.json(relatorio)


def main() -> None:
    st.title("🌦️ Clima pelo CEP")
    st.write("Digite um CEP para ver o clima atual e a previsão do tempo da cidade correspondente.")

    with st.sidebar:
        st.header("Sobre")
        st.markdown(
            "Dados de endereço: [ViaCEP](https://viacep.com.br)  \n"
            "Coordenadas e clima: [Open-Meteo](https://open-meteo.com)  \n\n"
            "A previsão é feita no nível da **cidade** do CEP."
        )
        dias = st.slider("Dias de previsão", min_value=3, max_value=16, value=7)

    with st.form("busca"):
        col_cep, col_botao = st.columns([4, 1], vertical_alignment="bottom")
        cep = col_cep.text_input("CEP", placeholder="Ex.: 01310-100", max_chars=10)
        enviado = col_botao.form_submit_button("Consultar", width="stretch")

    if not enviado:
        return

    try:
        with st.spinner("Consultando ViaCEP e Open-Meteo..."):
            relatorio = consultar_clima(cep, dias)
    except CepInvalidoError as erro:
        st.warning(f"✏️ {erro.mensagem}")
    except CepNaoEncontradoError as erro:
        st.warning(f"🔎 {erro.mensagem} Confira se digitou corretamente.")
    except LocalizacaoNaoEncontradaError as erro:
        st.error(f"🗺️ {erro.mensagem}")
    except ApiExternaError as erro:
        st.error(f"🌐 Serviço externo indisponível: {erro.mensagem} Tente novamente em instantes.")
    else:
        exibir_relatorio(relatorio)


main()
