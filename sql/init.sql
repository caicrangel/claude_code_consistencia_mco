CREATE DATABASE IF NOT EXISTS mco
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE mco;

CREATE TABLE IF NOT EXISTS parametro_linha (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    codigo_externo  VARCHAR(20)  NOT NULL,
    sublinha        VARCHAR(10)  NOT NULL,
    nome_linha      VARCHAR(255) NULL,
    extensao_metros INT          NOT NULL,
    ativo           TINYINT(1)   NOT NULL DEFAULT 1,
    criado_em       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_linha_sublinha (codigo_externo, sublinha)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS lote_importacao (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    nome_arquivo    VARCHAR(255) NOT NULL,
    qtd_linhas      INT          NOT NULL DEFAULT 0,
    qtd_inseridas   INT          NOT NULL DEFAULT 0,
    qtd_duplicadas  INT          NOT NULL DEFAULT 0,
    importado_em    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS viagem_mco (
    id                       BIGINT AUTO_INCREMENT PRIMARY KEY,
    lote_id                  INT          NOT NULL,
    nome_operadora           VARCHAR(150) NULL,
    nome_garagem             VARCHAR(150) NULL,
    codigo_interno_linha     VARCHAR(30)  NULL,
    codigo_externo_linha     VARCHAR(20)  NOT NULL,
    nome_linha               VARCHAR(255) NULL,
    tipo_viagem              VARCHAR(20)  NULL,
    numero_veiculo           VARCHAR(20)  NULL,
    desc_tipo_veiculo        VARCHAR(50)  NULL,
    sublinha                 VARCHAR(10)  NOT NULL,
    data_hora_inicio         DATETIME     NULL,
    data_hora_fim            DATETIME     NULL,
    catraca_inicial          BIGINT       NULL,
    catraca_final            BIGINT       NULL,
    distancia_metros         INT          NOT NULL DEFAULT 0,
    viagem_id_externo        VARCHAR(30)  NULL,
    INDEX ix_lote (lote_id),
    INDEX ix_linha_sublinha (codigo_externo_linha, sublinha),
    INDEX ix_inicio (data_hora_inicio),
    UNIQUE KEY uq_viagem_externa (viagem_id_externo),
    CONSTRAINT fk_viagem_lote FOREIGN KEY (lote_id) REFERENCES lote_importacao(id) ON DELETE CASCADE
) ENGINE=InnoDB;
