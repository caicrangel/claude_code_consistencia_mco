from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date, datetime
from typing import IO

import pandas as pd
from sqlalchemy.dialects.mysql import insert as mysql_insert

from app.db import session_scope
from app.models import LoteImportacao, ViagemMCO


# Mapeamento direto coluna do CSV -> campo do modelo.
# Observações:
#  - "Viagem" aparece DUAS vezes no CSV: a coluna H é o tipo (Nor./Extra),
#    a coluna W é o ID numérico da viagem. Pandas renomeia a segunda como "Viagem.1".
#  - Aqui mapeamos a primeira ocorrência ("Viagem") como tipo_viagem.
#    A segunda ("Viagem.1") é tratada à parte como viagem_id_externo.
COLUNAS_TEXTO = {
    "Código Operadora": "codigo_operadora",
    "Nome Operadora": "nome_operadora",
    "Nome Garagem": "nome_garagem",
    "Código Interno Linha": "codigo_interno_linha",
    "Código Externo Linha": "codigo_externo_linha",
    "Nome Linha": "nome_linha",
    "Num Terminal": "num_terminal",
    "Viagem": "tipo_viagem",
    "Código Veículo": "codigo_veiculo",
    "Numero Veículo": "numero_veiculo",
    "Desc. Tipo Veículo": "desc_tipo_veiculo",
    "Código Equipamento": "codigo_equipamento",
    "Numero de Série do Equipamento": "numero_serie_equipamento",
    "Sub Linha": "sublinha",
    "Cartão Motorista": "cartao_motorista",
    "Cartão Cobrador": "cartao_cobrador",
    "Orgão Gestor": "orgao_gestor",
    "CMP TER SUB": "cmp_ter_sub",
    "Tipo Viagem": "tipo_viagem_codigo",
    "Intervalo Viagem": "intervalo_viagem",
    "Terminal": "terminal",
    "Tipo Data": "tipo_data",
}

COLUNAS_INT = {
    "Catraca Pendente": "catraca_pendente",
    "Catraca Inicial": "catraca_inicial",
    "Catraca Final": "catraca_final",
    "Distância": "distancia_metros",
    "Coleta Pendente": "coleta_pendente",
    "Passageiros": "passageiros",
    "Inteiras": "inteiras",
    "VT": "vt",
    "VT Integração": "vt_integracao",
    "Gratuidade": "gratuidade",
    "Passagens": "passagens",
    "Bilhete Unitário": "bilhete_unitario",
    "Passagens Integração": "passagens_integracao",
    "Estudantes": "estudantes",
    "EStudantes Integração": "estudantes_integracao",
}

COLUNAS_DATETIME = {
    "Data Hora Início Operação": "data_hora_inicio",
    "Data Hora Final Operação": "data_hora_fim",
    "Data Hora Saída Terminal": "data_hora_saida_terminal",
    "Data Hora Início": "data_hora_inicio_alt",
    "Data Hora Inserção": "data_hora_insercao",
}

COLUNAS_DATE = {
    "Data Coleta": "data_coleta",
}

COLUNAS_OBRIGATORIAS_MIN = [
    "Código Externo Linha",
    "Sub Linha",
    "Distância",
]


@dataclass
class ResultadoImportacao:
    lote_id: int
    qtd_linhas: int
    qtd_inseridas: int
    qtd_duplicadas: int
    erros: list[str]


def _to_int(value) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if not s or s.lower() in ("nan", "none"):
        return None
    try:
        return int(float(s.replace(",", ".")))
    except (ValueError, TypeError):
        return None


def _to_str(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    return s or None


def _to_datetime(value) -> datetime | None:
    s = _to_str(value)
    if s is None:
        return None
    dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
    if pd.isna(dt):
        return None
    return dt.to_pydatetime()


def _to_date(value) -> date | None:
    dt = _to_datetime(value)
    return dt.date() if dt else None


def ler_csv_mco(file: IO | bytes | str) -> pd.DataFrame:
    """Lê CSV MCO no padrão BR (separador ; e decimal ,) com fallback de encoding."""
    if isinstance(file, bytes):
        buffer = io.BytesIO(file)
    elif hasattr(file, "read"):
        buffer = file
    else:
        buffer = file

    for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            if hasattr(buffer, "seek"):
                buffer.seek(0)
            return pd.read_csv(
                buffer,
                sep=";",
                decimal=",",
                dtype=str,
                encoding=encoding,
                keep_default_na=True,
            )
        except UnicodeDecodeError:
            continue
    raise ValueError("Não foi possível decodificar o CSV (tentei utf-8 e latin-1).")


def validar_colunas(df: pd.DataFrame) -> list[str]:
    return [c for c in COLUNAS_OBRIGATORIAS_MIN if c not in df.columns]


def _df_para_registros(df: pd.DataFrame) -> list[dict]:
    registros: list[dict] = []
    for _, row in df.iterrows():
        rec: dict = {}

        for orig, dest in COLUNAS_TEXTO.items():
            if orig in df.columns:
                rec[dest] = _to_str(row.get(orig))

        for orig, dest in COLUNAS_INT.items():
            if orig in df.columns:
                rec[dest] = _to_int(row.get(orig))

        for orig, dest in COLUNAS_DATETIME.items():
            if orig in df.columns:
                rec[dest] = _to_datetime(row.get(orig))

        for orig, dest in COLUNAS_DATE.items():
            if orig in df.columns:
                rec[dest] = _to_date(row.get(orig))

        # ID externo da viagem é a 2ª ocorrência de "Viagem" no header
        # (pandas renomeia para "Viagem.1").
        viagem_id_raw = row.get("Viagem.1") if "Viagem.1" in df.columns else None
        rec["viagem_id_externo"] = _to_str(viagem_id_raw)

        # Distância é NOT NULL DEFAULT 0
        if rec.get("distancia_metros") is None:
            rec["distancia_metros"] = 0

        if not rec.get("codigo_externo_linha") or not rec.get("sublinha"):
            continue

        registros.append(rec)
    return registros


def importar_mco(file: IO | bytes, nome_arquivo: str) -> ResultadoImportacao:
    df = ler_csv_mco(file)

    faltando = validar_colunas(df)
    if faltando:
        return ResultadoImportacao(
            lote_id=0, qtd_linhas=0, qtd_inseridas=0, qtd_duplicadas=0,
            erros=[f"Colunas obrigatórias ausentes: {', '.join(faltando)}"],
        )

    registros = _df_para_registros(df)

    with session_scope() as s:
        lote = LoteImportacao(nome_arquivo=nome_arquivo, qtd_linhas=len(registros))
        s.add(lote)
        s.flush()

        inseridas = 0
        duplicadas = 0

        if registros:
            for r in registros:
                r["lote_id"] = lote.id

            stmt = mysql_insert(ViagemMCO.__table__).values(registros)
            stmt = stmt.prefix_with("IGNORE")
            result = s.execute(stmt)
            inseridas = result.rowcount or 0
            duplicadas = len(registros) - inseridas

        lote.qtd_inseridas = inseridas
        lote.qtd_duplicadas = duplicadas

        return ResultadoImportacao(
            lote_id=lote.id,
            qtd_linhas=len(registros),
            qtd_inseridas=inseridas,
            qtd_duplicadas=duplicadas,
            erros=[],
        )
