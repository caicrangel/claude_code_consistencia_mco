-- Migração 001: adicionar todas as colunas restantes do CSV MCO em viagem_mco.
-- Aplicar em bancos já criados pela versão inicial do init.sql.
-- Idempotente quando rodado em MySQL 8+ (suporta IF NOT EXISTS em ALTER TABLE ADD COLUMN).

USE mco;

ALTER TABLE viagem_mco
    ADD COLUMN IF NOT EXISTS codigo_operadora         VARCHAR(30)  NULL AFTER lote_id,
    ADD COLUMN IF NOT EXISTS num_terminal             VARCHAR(30)  NULL AFTER nome_linha,
    ADD COLUMN IF NOT EXISTS codigo_veiculo           VARCHAR(30)  NULL AFTER tipo_viagem,
    ADD COLUMN IF NOT EXISTS codigo_equipamento       VARCHAR(30)  NULL AFTER desc_tipo_veiculo,
    ADD COLUMN IF NOT EXISTS numero_serie_equipamento VARCHAR(50)  NULL AFTER codigo_equipamento,
    ADD COLUMN IF NOT EXISTS cartao_motorista         VARCHAR(30)  NULL AFTER data_hora_fim,
    ADD COLUMN IF NOT EXISTS cartao_cobrador          VARCHAR(30)  NULL AFTER cartao_motorista,
    ADD COLUMN IF NOT EXISTS catraca_pendente         TINYINT      NULL AFTER cartao_cobrador,
    ADD COLUMN IF NOT EXISTS orgao_gestor             VARCHAR(30)  NULL AFTER viagem_id_externo,
    ADD COLUMN IF NOT EXISTS cmp_ter_sub              VARCHAR(30)  NULL AFTER orgao_gestor,
    ADD COLUMN IF NOT EXISTS tipo_viagem_codigo       VARCHAR(20)  NULL AFTER cmp_ter_sub,
    ADD COLUMN IF NOT EXISTS data_hora_saida_terminal DATETIME     NULL AFTER tipo_viagem_codigo,
    ADD COLUMN IF NOT EXISTS coleta_pendente          TINYINT      NULL AFTER data_hora_saida_terminal,
    ADD COLUMN IF NOT EXISTS passageiros              INT          NULL AFTER coleta_pendente,
    ADD COLUMN IF NOT EXISTS inteiras                 INT          NULL AFTER passageiros,
    ADD COLUMN IF NOT EXISTS vt                       INT          NULL AFTER inteiras,
    ADD COLUMN IF NOT EXISTS vt_integracao            INT          NULL AFTER vt,
    ADD COLUMN IF NOT EXISTS gratuidade               INT          NULL AFTER vt_integracao,
    ADD COLUMN IF NOT EXISTS passagens                INT          NULL AFTER gratuidade,
    ADD COLUMN IF NOT EXISTS bilhete_unitario         INT          NULL AFTER passagens,
    ADD COLUMN IF NOT EXISTS passagens_integracao     INT          NULL AFTER bilhete_unitario,
    ADD COLUMN IF NOT EXISTS estudantes               INT          NULL AFTER passagens_integracao,
    ADD COLUMN IF NOT EXISTS estudantes_integracao    INT          NULL AFTER estudantes,
    ADD COLUMN IF NOT EXISTS intervalo_viagem         VARCHAR(20)  NULL AFTER estudantes_integracao,
    ADD COLUMN IF NOT EXISTS terminal                 VARCHAR(30)  NULL AFTER intervalo_viagem,
    ADD COLUMN IF NOT EXISTS data_coleta              DATE         NULL AFTER terminal,
    ADD COLUMN IF NOT EXISTS tipo_data                VARCHAR(30)  NULL AFTER data_coleta,
    ADD COLUMN IF NOT EXISTS data_hora_inicio_alt     DATETIME     NULL AFTER tipo_data,
    ADD COLUMN IF NOT EXISTS data_hora_insercao       DATETIME     NULL AFTER data_hora_inicio_alt;

-- Índices adicionais (idempotentes em MySQL 8+)
ALTER TABLE viagem_mco
    ADD INDEX IF NOT EXISTS ix_veiculo (numero_veiculo),
    ADD INDEX IF NOT EXISTS ix_operadora (nome_operadora);
