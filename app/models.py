from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class ParametroLinha(Base):
    __tablename__ = "parametro_linha"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo_externo = Column(String(20), nullable=False)
    sublinha = Column(String(10), nullable=False)
    nome_linha = Column(String(255), nullable=True)
    extensao_metros = Column(Integer, nullable=False)
    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    atualizado_em = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("codigo_externo", "sublinha", name="uq_linha_sublinha"),
    )

    @property
    def extensao_km(self) -> float:
        return self.extensao_metros / 1000.0


class LoteImportacao(Base):
    __tablename__ = "lote_importacao"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome_arquivo = Column(String(255), nullable=False)
    qtd_linhas = Column(Integer, nullable=False, default=0)
    qtd_inseridas = Column(Integer, nullable=False, default=0)
    qtd_duplicadas = Column(Integer, nullable=False, default=0)
    importado_em = Column(DateTime, nullable=False, default=datetime.utcnow)

    viagens = relationship("ViagemMCO", back_populates="lote", cascade="all, delete-orphan")


class ViagemMCO(Base):
    __tablename__ = "viagem_mco"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    lote_id = Column(Integer, ForeignKey("lote_importacao.id", ondelete="CASCADE"), nullable=False)
    nome_operadora = Column(String(150), nullable=True)
    nome_garagem = Column(String(150), nullable=True)
    codigo_interno_linha = Column(String(30), nullable=True)
    codigo_externo_linha = Column(String(20), nullable=False)
    nome_linha = Column(String(255), nullable=True)
    tipo_viagem = Column(String(20), nullable=True)
    numero_veiculo = Column(String(20), nullable=True)
    desc_tipo_veiculo = Column(String(50), nullable=True)
    sublinha = Column(String(10), nullable=False)
    data_hora_inicio = Column(DateTime, nullable=True)
    data_hora_fim = Column(DateTime, nullable=True)
    catraca_inicial = Column(BigInteger, nullable=True)
    catraca_final = Column(BigInteger, nullable=True)
    distancia_metros = Column(Integer, nullable=False, default=0)
    viagem_id_externo = Column(String(30), nullable=True)

    lote = relationship("LoteImportacao", back_populates="viagens")

    __table_args__ = (
        UniqueConstraint("viagem_id_externo", name="uq_viagem_externa"),
        Index("ix_lote", "lote_id"),
        Index("ix_linha_sublinha", "codigo_externo_linha", "sublinha"),
        Index("ix_inicio", "data_hora_inicio"),
    )
