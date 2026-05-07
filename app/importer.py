from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime
from typing import IO

import pandas as pd
from sqlalchemy.dialects.mysql import insert as mysql_insert

from app.db import session_scope
from app.models import LoteImportacao, ViagemMCO


COLUNAS_ESPERADAS = {
    "Nome Operadora": "nome_operadora",
    "Nome Garagem": "nome_garagem",
    "Código Interno Linha": "codigo_interno_linha",
    "Código Externo Linha": "codigo_externo_linha",
    "Nome Linha": "nome_linha",
    "Viagem": "tipo_viagem",
    "Numero Veículo": "numero_veiculo",
    "Desc. Tipo Veículo": "desc_tipo_veiculo",
    "Sub Linha": "sublinha",
    "Data Hora Início Operação": "data_hora_inicio",
    "Data Hora Final Operação": "data_hora_fim",
    "Catraca Inicial": "catraca_inicial",
    "Catraca Final": "catraca_final",
    "Distância": "distancia_metros",
}

COLUNA_VIAGEM_ID = "Viagem"
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
    if pd.isna(value):
        return None
    try:
        return int(float(str(value).replace(",", ".")))
    except (ValueError, TypeError):
        return None


def _to_datetime(value) -> datetime | None:
    if pd.isna(value):
        return None
    try:
        return pd.to_datetime(value, errors="coerce").to_pydatetime()
    except Exception:
        return None


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
            df = pd.read_csv(
                buffer,
                sep=";",
                decimal=",",
                dtype=str,
                encoding=encoding,
                keep_default_na=True,
            )
            return df
        except UnicodeDecodeError:
            continue
    raise ValueError("Não foi possível decodificar o CSV (tentei utf-8 e latin-1).")


def validar_colunas(df: pd.DataFrame) -> list[str]:
    faltando = [c for c in COLUNAS_OBRIGATORIAS_MIN if c not in df.columns]
    return faltando


def _df_para_registros(df: pd.DataFrame) -> list[dict]:
    registros = []
    for _, row in df.iterrows():
        rec = {dest: row.get(orig) for orig, dest in COLUNAS_ESPERADAS.items() if orig in df.columns}

        rec["catraca_inicial"] = _to_int(rec.get("catraca_inicial"))
        rec["catraca_final"] = _to_int(rec.get("catraca_final"))
        rec["distancia_metros"] = _to_int(rec.get("distancia_metros")) or 0
        rec["data_hora_inicio"] = _to_datetime(rec.get("data_hora_inicio"))
        rec["data_hora_fim"] = _to_datetime(rec.get("data_hora_fim"))

        # Coluna W "Viagem" no CSV vem depois da Distância e contém o ID externo da viagem.
        # No header BR, ambas se chamam "Viagem"; pandas renomeia a 2ª como "Viagem.1".
        viagem_id = row.get("Viagem.1") if "Viagem.1" in df.columns else None
        rec["viagem_id_externo"] = str(viagem_id).strip() if viagem_id and not pd.isna(viagem_id) else None

        for k in ("codigo_externo_linha", "sublinha", "numero_veiculo", "tipo_viagem"):
            if rec.get(k) is not None and not pd.isna(rec.get(k)):
                rec[k] = str(rec[k]).strip()
            else:
                rec[k] = None

        if not rec.get("codigo_externo_linha") or not rec.get("sublinha"):
            continue

        registros.append(rec)
    return registros


def importar_mco(file: IO | bytes, nome_arquivo: str) -> ResultadoImportacao:
    df = ler_csv_mco(file)
    erros: list[str] = []

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
            erros=erros,
        )
