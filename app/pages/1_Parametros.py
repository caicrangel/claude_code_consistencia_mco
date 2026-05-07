import pandas as pd
import streamlit as st
from sqlalchemy import select

from app.db import session_scope
from app.models import ParametroLinha

st.set_page_config(page_title="Parâmetros", page_icon="📋", layout="wide")
st.title("📋 Parâmetros — Extensão por Linha/Sublinha")

st.caption(
    "Cadastre a extensão programada de cada combinação **Código Externo Linha + Sublinha**. "
    "A extensão é em **metros** (ex.: 14000 = 14 km)."
)

tab_listar, tab_novo, tab_importar = st.tabs(["📑 Listar / Editar", "➕ Novo", "📥 Importar Excel/CSV"])


def _carregar() -> pd.DataFrame:
    with session_scope() as s:
        rows = s.execute(
            select(
                ParametroLinha.id,
                ParametroLinha.codigo_externo,
                ParametroLinha.sublinha,
                ParametroLinha.nome_linha,
                ParametroLinha.extensao_metros,
                ParametroLinha.ativo,
            ).order_by(ParametroLinha.codigo_externo, ParametroLinha.sublinha)
        ).all()
    df = pd.DataFrame(rows, columns=["id", "codigo_externo", "sublinha", "nome_linha", "extensao_metros", "ativo"])
    if not df.empty:
        df["extensao_km"] = (df["extensao_metros"] / 1000).round(3)
    return df


with tab_listar:
    df = _carregar()
    st.metric("Total de parâmetros cadastrados", len(df))

    if df.empty:
        st.info("Nenhum parâmetro cadastrado ainda. Use a aba **Novo** ou **Importar Excel/CSV**.")
    else:
        edited = st.data_editor(
            df,
            num_rows="fixed",
            use_container_width=True,
            disabled=["id", "extensao_km"],
            column_config={
                "extensao_metros": st.column_config.NumberColumn("Extensão (m)", min_value=0, step=100),
                "extensao_km": st.column_config.NumberColumn("Extensão (km)", format="%.3f"),
                "ativo": st.column_config.CheckboxColumn("Ativo"),
            },
            key="editor_param",
        )

        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("💾 Salvar alterações", type="primary"):
                with session_scope() as s:
                    for _, row in edited.iterrows():
                        p = s.get(ParametroLinha, int(row["id"]))
                        if p is None:
                            continue
                        p.codigo_externo = str(row["codigo_externo"]).strip()
                        p.sublinha = str(row["sublinha"]).strip()
                        p.nome_linha = (row["nome_linha"] or None) and str(row["nome_linha"]).strip()
                        p.extensao_metros = int(row["extensao_metros"])
                        p.ativo = bool(row["ativo"])
                st.success("Alterações salvas.")
                st.rerun()

with tab_novo:
    with st.form("form_novo_param", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        codigo = c1.text_input("Código Externo Linha *", placeholder="AC02")
        sublinha = c2.text_input("Sublinha *", placeholder="1")
        ext_m = c3.number_input("Extensão (metros) *", min_value=0, step=100, value=14000)
        nome = st.text_input("Nome da linha", placeholder="ESTAÇÃO TRANSF. MINAS CAIXA")

        submitted = st.form_submit_button("Cadastrar", type="primary")
        if submitted:
            if not codigo.strip() or not sublinha.strip() or ext_m <= 0:
                st.error("Preencha código externo, sublinha e extensão > 0.")
            else:
                try:
                    with session_scope() as s:
                        p = ParametroLinha(
                            codigo_externo=codigo.strip(),
                            sublinha=sublinha.strip(),
                            nome_linha=nome.strip() or None,
                            extensao_metros=int(ext_m),
                            ativo=True,
                        )
                        s.add(p)
                    st.success(f"Parâmetro {codigo}/{sublinha} cadastrado.")
                except Exception as e:
                    st.error(f"Erro ao cadastrar (provável duplicata): {e}")

with tab_importar:
    st.write(
        "Suba uma planilha com as colunas: "
        "`codigo_externo`, `sublinha`, `extensao_metros` e opcionalmente `nome_linha`."
    )
    arq = st.file_uploader("Excel ou CSV", type=["xlsx", "xls", "csv"], key="upload_param")
    if arq is not None:
        if arq.name.lower().endswith(".csv"):
            df_imp = pd.read_csv(arq, sep=None, engine="python")
        else:
            df_imp = pd.read_excel(arq)
        df_imp.columns = [c.strip().lower() for c in df_imp.columns]

        obrig = {"codigo_externo", "sublinha", "extensao_metros"}
        falt = obrig - set(df_imp.columns)
        if falt:
            st.error(f"Colunas faltando: {', '.join(falt)}")
        else:
            st.dataframe(df_imp.head(20), use_container_width=True)
            if st.button(f"📥 Inserir/atualizar {len(df_imp)} parâmetros", type="primary"):
                ins = upd = 0
                with session_scope() as s:
                    for _, row in df_imp.iterrows():
                        ce = str(row["codigo_externo"]).strip()
                        sl = str(row["sublinha"]).strip()
                        em = int(row["extensao_metros"])
                        nm = str(row.get("nome_linha", "") or "").strip() or None
                        existente = s.execute(
                            select(ParametroLinha).where(
                                ParametroLinha.codigo_externo == ce,
                                ParametroLinha.sublinha == sl,
                            )
                        ).scalar_one_or_none()
                        if existente:
                            existente.extensao_metros = em
                            if nm:
                                existente.nome_linha = nm
                            upd += 1
                        else:
                            s.add(ParametroLinha(
                                codigo_externo=ce, sublinha=sl,
                                extensao_metros=em, nome_linha=nm, ativo=True,
                            ))
                            ins += 1
                st.success(f"Inseridos: {ins}  |  Atualizados: {upd}")
                st.rerun()
