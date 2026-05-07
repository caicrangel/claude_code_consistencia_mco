from __future__ import annotations

from datetime import date, datetime, time
from typing import Iterable

import pandas as pd
from sqlalchemy import select

from app.config import PERCENTUAL_MINIMO
from app.db import session_scope
from app.models import ParametroLinha, ViagemMCO

STATUS_ATENDEU = "ATENDEU"
STATUS_NAO_ATENDEU = "NAO_ATENDEU"
STATUS_ZERADA = "ZERADA"
STATUS_SEM_PARAMETRO = "SEM_PARAMETRO"


def _classificar(distancia_m: int, extensao_m: int | None, percentual_min: float) -> tuple[str, float | None]:
    if distancia_m == 0:
        return STATUS_ZERADA, 0.0 if extensao_m else None
    if not extensao_m or extensao_m <= 0:
        return STATUS_SEM_PARAMETRO, None
    pct = (distancia_m / extensao_m) * 100.0
    return (STATUS_ATENDEU if pct >= percentual_min else STATUS_NAO_ATENDEU, pct)


def consistir_lote(
    lote_id: int | None = None,
    percentual_min: float | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    operadoras: Iterable[str] | None = None,
    garagens: Iterable[str] | None = None,
    linhas: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Cruza viagens (com filtros opcionais) e parâmetros, classificando cada viagem."""
    pmin = percentual_min if percentual_min is not None else PERCENTUAL_MINIMO

    with session_scope() as s:
        params_rows = s.execute(
            select(
                ParametroLinha.codigo_externo,
                ParametroLinha.sublinha,
                ParametroLinha.extensao_metros,
                ParametroLinha.nome_linha,
            ).where(ParametroLinha.ativo == True)  # noqa: E712
        ).all()
        params = {
            (r.codigo_externo, str(r.sublinha)): {
                "extensao_metros": r.extensao_metros,
                "nome_linha_param": r.nome_linha,
            }
            for r in params_rows
        }

        stmt = select(
            ViagemMCO.id,
            ViagemMCO.lote_id,
            ViagemMCO.codigo_externo_linha,
            ViagemMCO.sublinha,
            ViagemMCO.nome_linha,
            ViagemMCO.tipo_viagem,
            ViagemMCO.numero_veiculo,
            ViagemMCO.nome_operadora,
            ViagemMCO.nome_garagem,
            ViagemMCO.data_hora_inicio,
            ViagemMCO.data_hora_fim,
            ViagemMCO.distancia_metros,
        )
        if lote_id is not None:
            stmt = stmt.where(ViagemMCO.lote_id == lote_id)
        if data_inicio is not None:
            stmt = stmt.where(ViagemMCO.data_hora_inicio >= datetime.combine(data_inicio, time.min))
        if data_fim is not None:
            stmt = stmt.where(ViagemMCO.data_hora_inicio <= datetime.combine(data_fim, time.max))
        if operadoras:
            stmt = stmt.where(ViagemMCO.nome_operadora.in_(list(operadoras)))
        if garagens:
            stmt = stmt.where(ViagemMCO.nome_garagem.in_(list(garagens)))
        if linhas:
            stmt = stmt.where(ViagemMCO.codigo_externo_linha.in_(list(linhas)))

        viagens = s.execute(stmt).all()

    rows = []
    for v in viagens:
        chave = (v.codigo_externo_linha, str(v.sublinha))
        p = params.get(chave)
        ext = p["extensao_metros"] if p else None
        status, pct = _classificar(v.distancia_metros or 0, ext, pmin)
        rows.append({
            "viagem_id": v.id,
            "lote_id": v.lote_id,
            "operadora": v.nome_operadora,
            "garagem": v.nome_garagem,
            "linha": v.codigo_externo_linha,
            "sublinha": v.sublinha,
            "nome_linha": v.nome_linha,
            "tipo_viagem": v.tipo_viagem,
            "veiculo": v.numero_veiculo,
            "inicio": v.data_hora_inicio,
            "fim": v.data_hora_fim,
            "distancia_m": v.distancia_metros or 0,
            "extensao_param_m": ext,
            "pct_cumprimento": round(pct, 2) if pct is not None else None,
            "status": status,
        })

    return pd.DataFrame(rows)


def resumo_por_status(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["status", "qtd"])
    return df.groupby("status", as_index=False).size().rename(columns={"size": "qtd"})


def veiculos_zerados(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["status"] == STATUS_ZERADA].copy()
