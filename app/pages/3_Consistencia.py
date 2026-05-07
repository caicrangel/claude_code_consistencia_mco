import io

import pandas as pd
import streamlit as st
from sqlalchemy import select, desc

from app.config import PERCENTUAL_MINIMO
from app.consistency import (
    STATUS_ATENDEU, STATUS_NAO_ATENDEU, STATUS_SEM_PARAMETRO, STATUS_ZERADA,
    consistir_lote, resumo_por_status, veiculos_zerados,
)
from app.db import session_scope
from app.models import LoteImportacao

st.set_page_config(page_title="Consistência", page_icon="📊", layout="wide")
st.title("📊 Consistência das Viagens")

with session_scope() as s:
    lotes = s.execute(
        select(LoteImportacao.id, LoteImportacao.nome_arquivo, LoteImportacao.importado_em)
        .order_by(desc(LoteImportacao.importado_em))
    ).all()

if not lotes:
    st.info("Nenhum lote importado. Vá em **Importar MCO** para começar.")
    st.stop()

opcoes = {f"#{l.id} — {l.nome_arquivo} ({l.importado_em:%d/%m/%Y %H:%M})": l.id for l in lotes}
opcoes_full = {"📦 Todos os lotes": None, **opcoes}

c1, c2 = st.columns([3, 1])
with c1:
    escolha = st.selectbox("Lote", list(opcoes_full.keys()))
with c2:
    pmin = st.number_input("% mínimo", min_value=50.0, max_value=100.0, value=float(PERCENTUAL_MINIMO), step=1.0)

lote_id = opcoes_full[escolha]
df = consistir_lote(lote_id=lote_id, percentual_min=pmin)

if df.empty:
    st.warning("Sem viagens para esse filtro.")
    st.stop()

resumo = resumo_por_status(df)
total = len(df)

st.subheader("Resumo")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total", total)
m2.metric("✅ Atendeu", int(resumo.loc[resumo.status == STATUS_ATENDEU, "qtd"].sum()))
m3.metric("❌ Não atendeu", int(resumo.loc[resumo.status == STATUS_NAO_ATENDEU, "qtd"].sum()))
m4.metric("⚠️ Zeradas", int(resumo.loc[resumo.status == STATUS_ZERADA, "qtd"].sum()))
m5.metric("❓ Sem parâmetro", int(resumo.loc[resumo.status == STATUS_SEM_PARAMETRO, "qtd"].sum()))

st.divider()

# Filtros
fcol1, fcol2, fcol3 = st.columns(3)
with fcol1:
    f_status = st.multiselect(
        "Filtrar por status",
        [STATUS_ATENDEU, STATUS_NAO_ATENDEU, STATUS_ZERADA, STATUS_SEM_PARAMETRO],
        default=[STATUS_NAO_ATENDEU, STATUS_ZERADA, STATUS_SEM_PARAMETRO],
    )
with fcol2:
    linhas_disp = sorted(df["linha"].dropna().unique().tolist())
    f_linha = st.multiselect("Linha", linhas_disp)
with fcol3:
    veic_disp = sorted(df["veiculo"].dropna().unique().tolist())
    f_veic = st.multiselect("Veículo", veic_disp)

dff = df.copy()
if f_status:
    dff = dff[dff["status"].isin(f_status)]
if f_linha:
    dff = dff[dff["linha"].isin(f_linha)]
if f_veic:
    dff = dff[dff["veiculo"].isin(f_veic)]

st.subheader(f"Detalhes ({len(dff)} viagens)")
st.dataframe(
    dff,
    use_container_width=True,
    column_config={
        "pct_cumprimento": st.column_config.NumberColumn("% cumprido", format="%.2f%%"),
        "distancia_m": st.column_config.NumberColumn("Distância (m)"),
        "extensao_param_m": st.column_config.NumberColumn("Extensão prog. (m)"),
    },
    hide_index=True,
)

st.divider()
st.subheader("⚠️ Veículos com distância zerada")
zer = veiculos_zerados(df)
if zer.empty:
    st.success("Nenhuma viagem zerada nesse recorte.")
else:
    agg = (
        zer.groupby(["veiculo", "linha", "sublinha"], dropna=False)
        .size()
        .reset_index(name="qtd_viagens_zeradas")
        .sort_values("qtd_viagens_zeradas", ascending=False)
    )
    st.dataframe(agg, use_container_width=True, hide_index=True)

st.divider()

# Export
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as writer:
    dff.to_excel(writer, sheet_name="viagens", index=False)
    resumo.to_excel(writer, sheet_name="resumo", index=False)
    if not zer.empty:
        zer.to_excel(writer, sheet_name="zeradas", index=False)

st.download_button(
    "📥 Baixar relatório (Excel)",
    data=buf.getvalue(),
    file_name=f"consistencia_lote_{lote_id or 'todos'}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
