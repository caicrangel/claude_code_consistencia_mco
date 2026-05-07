import pandas as pd
import streamlit as st
from sqlalchemy import select, desc

from app.db import session_scope
from app.importer import importar_mco, ler_csv_mco, validar_colunas
from app.models import LoteImportacao

st.set_page_config(page_title="Importar MCO", page_icon="📥", layout="wide")
st.title("📥 Importar MCO")

st.caption(
    "Suba o CSV diário do MCO (separador `;`, decimal `,`). "
    "Linhas com mesmo `Viagem` (ID externo) já importadas serão ignoradas."
)

arq = st.file_uploader("Arquivo CSV do MCO", type=["csv"])

if arq is not None:
    try:
        df_preview = ler_csv_mco(arq.getvalue())
    except Exception as e:
        st.error(f"Falha ao ler o arquivo: {e}")
        st.stop()

    faltando = validar_colunas(df_preview)
    if faltando:
        st.error(f"Colunas obrigatórias ausentes: {', '.join(faltando)}")
        st.stop()

    st.success(f"Arquivo carregado: **{len(df_preview)}** linhas detectadas.")
    st.write("**Pré-visualização (10 primeiras linhas):**")
    st.dataframe(df_preview.head(10), use_container_width=True)

    if st.button("🚀 Importar para o banco", type="primary"):
        with st.spinner("Importando..."):
            res = importar_mco(arq.getvalue(), nome_arquivo=arq.name)

        if res.erros:
            for e in res.erros:
                st.error(e)
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Lote", res.lote_id)
            c2.metric("Linhas no arquivo", res.qtd_linhas)
            c3.metric("Inseridas", res.qtd_inseridas)
            c4.metric("Duplicadas (ignoradas)", res.qtd_duplicadas)
            st.success("Importação concluída. Vá para **Consistência** para conferir.")

st.divider()
st.subheader("Lotes importados")

with session_scope() as s:
    lotes = s.execute(
        select(
            LoteImportacao.id,
            LoteImportacao.nome_arquivo,
            LoteImportacao.qtd_linhas,
            LoteImportacao.qtd_inseridas,
            LoteImportacao.qtd_duplicadas,
            LoteImportacao.importado_em,
        ).order_by(desc(LoteImportacao.importado_em))
    ).all()

if lotes:
    st.dataframe(
        pd.DataFrame(lotes, columns=["id", "arquivo", "linhas", "inseridas", "duplicadas", "importado_em"]),
        use_container_width=True,
    )
else:
    st.info("Nenhum lote importado ainda.")
