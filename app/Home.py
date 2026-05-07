import streamlit as st

from app.config import PERCENTUAL_MINIMO

st.set_page_config(
    page_title="Consistência MCO",
    page_icon="🚌",
    layout="wide",
)

st.title("🚌 Consistência MCO — Mapa de Controle Operacional")

st.markdown(
    f"""
Ferramenta para conferir, dia a dia, se as viagens do MCO atingiram a quilometragem mínima
necessária para o pagamento da remuneração complementar.

**Regra de consistência**

- ✅ **ATENDEU**: distância realizada ≥ **{PERCENTUAL_MINIMO:.0f}%** da extensão programada
- ❌ **NÃO ATENDEU**: distância realizada < {PERCENTUAL_MINIMO:.0f}% e > 0
- ⚠️ **ZERADA**: distância = 0 (suspeita de falha no veículo/equipamento)
- ❓ **SEM PARÂMETRO**: linha+sublinha sem extensão cadastrada

**Como usar**

1. **Parâmetros** — cadastre a extensão (em metros) de cada `Linha + Sublinha`.
2. **Importar MCO** — suba o CSV diário. Linhas duplicadas (mesmo `Viagem` ID) são ignoradas.
3. **Consistência** — visualize os resultados, filtre por lote, exporte.
"""
)

st.info(
    "Use o menu lateral para navegar entre **Parâmetros**, **Importar MCO** e **Consistência**.",
    icon="👈",
)
