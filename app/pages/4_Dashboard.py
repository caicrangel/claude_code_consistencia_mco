from datetime import date, timedelta

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import func, select

from app.config import PERCENTUAL_MINIMO
from app.consistency import (
    STATUS_ATENDEU, STATUS_NAO_ATENDEU, STATUS_SEM_PARAMETRO, STATUS_ZERADA,
    consistir_lote,
)
from app.db import session_scope
from app.models import ViagemMCO

st.set_page_config(page_title="Dashboard", page_icon="📈", layout="wide")
st.title("📈 Dashboard Operacional")
st.caption("Indicadores agregados de cumprimento de quilometragem e ocorrências.")


# ---------------------------------------------------------------------------
# Filtros (sidebar)
# ---------------------------------------------------------------------------
with session_scope() as s:
    bounds = s.execute(
        select(
            func.min(ViagemMCO.data_hora_inicio),
            func.max(ViagemMCO.data_hora_inicio),
        )
    ).one()
    operadoras_disp = [
        r[0] for r in s.execute(
            select(ViagemMCO.nome_operadora).where(ViagemMCO.nome_operadora.isnot(None)).distinct()
        ).all()
    ]
    garagens_disp = [
        r[0] for r in s.execute(
            select(ViagemMCO.nome_garagem).where(ViagemMCO.nome_garagem.isnot(None)).distinct()
        ).all()
    ]
    linhas_disp = [
        r[0] for r in s.execute(
            select(ViagemMCO.codigo_externo_linha).distinct()
        ).all()
    ]

dt_min, dt_max = bounds
if dt_min is None or dt_max is None:
    st.info("Sem viagens importadas ainda. Vá em **Importar MCO**.")
    st.stop()

dt_min_d, dt_max_d = dt_min.date(), dt_max.date()
default_inicio = max(dt_min_d, dt_max_d - timedelta(days=6))

with st.sidebar:
    st.header("Filtros")
    periodo = st.date_input(
        "Período",
        value=(default_inicio, dt_max_d),
        min_value=dt_min_d,
        max_value=dt_max_d,
    )
    if isinstance(periodo, tuple) and len(periodo) == 2:
        d_ini, d_fim = periodo
    else:
        d_ini = d_fim = periodo  # type: ignore

    pmin = st.number_input(
        "% mínimo de cumprimento",
        min_value=50.0, max_value=100.0,
        value=float(PERCENTUAL_MINIMO), step=1.0,
    )
    f_op = st.multiselect("Operadora", sorted(operadoras_disp))
    f_gar = st.multiselect("Garagem", sorted(garagens_disp))
    f_lin = st.multiselect("Linha", sorted(linhas_disp))


# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------
df = consistir_lote(
    percentual_min=pmin,
    data_inicio=d_ini,
    data_fim=d_fim,
    operadoras=f_op or None,
    garagens=f_gar or None,
    linhas=f_lin or None,
)

if df.empty:
    st.warning("Sem viagens para os filtros selecionados.")
    st.stop()

df["dia"] = pd.to_datetime(df["inicio"]).dt.date
df["distancia_km"] = df["distancia_m"] / 1000.0
df["extensao_param_km"] = df["extensao_param_m"].astype("float") / 1000.0


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
total = len(df)
atend = (df["status"] == STATUS_ATENDEU).sum()
nao_atend = (df["status"] == STATUS_NAO_ATENDEU).sum()
zer = (df["status"] == STATUS_ZERADA).sum()
sem_par = (df["status"] == STATUS_SEM_PARAMETRO).sum()
pct_atend = (atend / total * 100) if total else 0.0
km_realizado = df["distancia_km"].sum()
km_programado = df["extensao_param_km"].fillna(0).sum()
veic_unicos_zerados = df.loc[df["status"] == STATUS_ZERADA, "veiculo"].nunique()

st.subheader("Indicadores")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Viagens", f"{total:,}".replace(",", "."))
c2.metric("% Atendimento", f"{pct_atend:.1f}%")
c3.metric("KM realizado", f"{km_realizado:,.1f}".replace(",", "."))
c4.metric("KM programado", f"{km_programado:,.1f}".replace(",", "."))

c5, c6, c7, c8 = st.columns(4)
c5.metric("✅ Atendeu", int(atend))
c6.metric("❌ Não atendeu", int(nao_atend))
c7.metric("⚠️ Zeradas", int(zer), help=f"{veic_unicos_zerados} veículo(s) distinto(s)")
c8.metric("❓ Sem parâmetro", int(sem_par))

st.divider()


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------
STATUS_COLORS = {
    STATUS_ATENDEU: "#22c55e",
    STATUS_NAO_ATENDEU: "#ef4444",
    STATUS_ZERADA: "#f59e0b",
    STATUS_SEM_PARAMETRO: "#94a3b8",
}
status_scale = alt.Scale(
    domain=list(STATUS_COLORS.keys()),
    range=list(STATUS_COLORS.values()),
)

g1, g2 = st.columns(2)

with g1:
    st.markdown("**Distribuição por status**")
    pie_df = df.groupby("status", as_index=False).size().rename(columns={"size": "qtd"})
    chart = (
        alt.Chart(pie_df)
        .mark_arc(innerRadius=60)
        .encode(
            theta=alt.Theta("qtd:Q"),
            color=alt.Color("status:N", scale=status_scale, legend=alt.Legend(title=None)),
            tooltip=["status", "qtd"],
        )
        .properties(height=280)
    )
    st.altair_chart(chart, use_container_width=True)

with g2:
    st.markdown("**Evolução diária do % de atendimento**")
    diario = (
        df.assign(_atend=(df["status"] == STATUS_ATENDEU).astype(int))
        .groupby("dia", as_index=False)
        .agg(viagens=("viagem_id", "count"), atendidas=("_atend", "sum"))
    )
    diario["pct"] = (diario["atendidas"] / diario["viagens"]) * 100
    line = (
        alt.Chart(diario)
        .mark_line(point=True, strokeWidth=3, color="#0ea5e9")
        .encode(
            x=alt.X("dia:T", title="Dia"),
            y=alt.Y("pct:Q", title="% Atendimento", scale=alt.Scale(domain=[0, 100])),
            tooltip=[
                alt.Tooltip("dia:T", title="Dia"),
                alt.Tooltip("viagens:Q", title="Viagens"),
                alt.Tooltip("atendidas:Q", title="Atendidas"),
                alt.Tooltip("pct:Q", title="%", format=".1f"),
            ],
        )
        .properties(height=280)
    )
    rule = alt.Chart(pd.DataFrame({"y": [pmin]})).mark_rule(
        color="#ef4444", strokeDash=[4, 4]
    ).encode(y="y:Q")
    st.altair_chart(line + rule, use_container_width=True)

st.divider()

g3, g4 = st.columns(2)

with g3:
    st.markdown("**% Atendimento por linha** (top 15 por volume)")
    by_linha = (
        df.assign(_atend=(df["status"] == STATUS_ATENDEU).astype(int))
        .groupby(["linha"], as_index=False)
        .agg(viagens=("viagem_id", "count"), atendidas=("_atend", "sum"))
    )
    by_linha["pct"] = (by_linha["atendidas"] / by_linha["viagens"]) * 100
    by_linha = by_linha.sort_values("viagens", ascending=False).head(15)
    bar = (
        alt.Chart(by_linha)
        .mark_bar()
        .encode(
            x=alt.X("pct:Q", title="% Atendimento", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("linha:N", sort="-x", title=None),
            color=alt.condition(
                alt.datum.pct >= pmin,
                alt.value("#22c55e"),
                alt.value("#ef4444"),
            ),
            tooltip=["linha", "viagens", "atendidas",
                     alt.Tooltip("pct:Q", title="%", format=".1f")],
        )
        .properties(height=380)
    )
    st.altair_chart(bar, use_container_width=True)

with g4:
    st.markdown("**Top 15 linhas com mais NÃO ATENDIMENTOS**")
    falhas_linha = (
        df[df["status"] == STATUS_NAO_ATENDEU]
        .groupby("linha", as_index=False)
        .size()
        .rename(columns={"size": "qtd_nao_atendeu"})
        .sort_values("qtd_nao_atendeu", ascending=False)
        .head(15)
    )
    if falhas_linha.empty:
        st.success("Sem ocorrências de não atendimento no período.")
    else:
        bar2 = (
            alt.Chart(falhas_linha)
            .mark_bar(color="#ef4444")
            .encode(
                x=alt.X("qtd_nao_atendeu:Q", title="Qtd. não atendeu"),
                y=alt.Y("linha:N", sort="-x", title=None),
                tooltip=["linha", "qtd_nao_atendeu"],
            )
            .properties(height=380)
        )
        st.altair_chart(bar2, use_container_width=True)

st.divider()

g5, g6 = st.columns(2)

with g5:
    st.markdown("**Top 15 veículos com mais viagens ZERADAS**")
    zer_df = (
        df[df["status"] == STATUS_ZERADA]
        .groupby(["veiculo", "operadora"], as_index=False, dropna=False)
        .size()
        .rename(columns={"size": "qtd_zeradas"})
        .sort_values("qtd_zeradas", ascending=False)
        .head(15)
    )
    if zer_df.empty:
        st.success("Nenhum veículo com viagem zerada no período. ")
    else:
        bar3 = (
            alt.Chart(zer_df)
            .mark_bar(color="#f59e0b")
            .encode(
                x=alt.X("qtd_zeradas:Q", title="Qtd. zeradas"),
                y=alt.Y("veiculo:N", sort="-x", title=None),
                tooltip=["veiculo", "operadora", "qtd_zeradas"],
            )
            .properties(height=380)
        )
        st.altair_chart(bar3, use_container_width=True)

with g6:
    st.markdown("**% Atendimento por operadora**")
    by_op = (
        df.assign(_atend=(df["status"] == STATUS_ATENDEU).astype(int))
        .groupby("operadora", as_index=False, dropna=False)
        .agg(viagens=("viagem_id", "count"), atendidas=("_atend", "sum"))
    )
    by_op["pct"] = (by_op["atendidas"] / by_op["viagens"]) * 100
    by_op = by_op.sort_values("pct", ascending=False)
    bar4 = (
        alt.Chart(by_op)
        .mark_bar()
        .encode(
            x=alt.X("pct:Q", title="% Atendimento", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("operadora:N", sort="-x", title=None),
            color=alt.condition(
                alt.datum.pct >= pmin,
                alt.value("#22c55e"),
                alt.value("#ef4444"),
            ),
            tooltip=["operadora", "viagens", "atendidas",
                     alt.Tooltip("pct:Q", title="%", format=".1f")],
        )
        .properties(height=380)
    )
    st.altair_chart(bar4, use_container_width=True)

st.divider()
st.caption(
    f"Período analisado: **{d_ini:%d/%m/%Y}** a **{d_fim:%d/%m/%Y}**  •  "
    f"Limite mínimo: **{pmin:.0f}%**"
)
