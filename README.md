# Consistência MCO

Ferramenta para conferir, dia a dia, se as viagens registradas no **MCO (Mapa de Controle Operacional)** atingiram a quilometragem mínima necessária para o pagamento da remuneração complementar — e identificar veículos com distância zerada, sinal típico de falha no equipamento.

A regra de negócio é simples:

> Se a viagem realizou **≥ 90%** da extensão programada da linha/sublinha, o pagamento é devido.
> Abaixo disso, é perdido.

## Funcionalidades

- **Cadastro de parâmetros** — extensão (em metros) de cada `Linha + Sublinha`, com cadastro manual ou importação em massa via Excel/CSV.
- **Importação diária do MCO** — upload do CSV (separador `;`, decimal `,`); deduplicação por `Viagem` ID externo (re-importar o mesmo arquivo é seguro).
- **Consistência por viagem** — classifica cada viagem em:
  - ✅ **ATENDEU** — distância realizada ≥ 90% da programada
  - ❌ **NÃO ATENDEU** — entre 0 e 90%
  - ⚠️ **ZERADA** — distância 0 (suspeita de falha no veículo/equipamento)
  - ❓ **SEM PARÂMETRO** — linha/sublinha sem extensão cadastrada
- **Dashboard operacional** — KPIs e gráficos por período, operadora, garagem e linha; evolução diária do % atendimento, ranking de linhas e top veículos com mais viagens zeradas.
- **Exportação Excel multiabas** (viagens, resumo, zeradas) direto da tela de Consistência.

## Stack

- **Streamlit** (multipage) para a UI
- **SQLAlchemy 2** + **PyMySQL** para acesso ao banco
- **MySQL 8** como persistência
- **Altair** para os gráficos do dashboard
- **Docker Compose** para subir tudo

## Como rodar

### Opção 1 — tudo via Docker (recomendado)

```bash
git clone <url-do-repo>
cd claude_code_consistencia_mco

# (opcional) configura variáveis personalizadas
cp .env.example .env

docker compose up -d --build
```

Acesse: **http://localhost:8501**

Containers que devem subir:

| Nome | Porta exposta |
|---|---|
| `mco-mysql` | 3306 |
| `mco-app` | 8501 |

### Opção 2 — Streamlit no host, MySQL no Docker

Útil para desenvolvimento com hot-reload do código.

```bash
docker compose up -d mysql
pip install -r requirements.txt
streamlit run app/Home.py
```

## Variáveis de ambiente

Configuráveis via `.env` (ver `.env.example`):

| Variável | Default | Descrição |
|---|---|---|
| `MYSQL_HOST` | `localhost` | host do MySQL (use `mysql` quando a app rodar em container) |
| `MYSQL_PORT` | `3306` | porta do MySQL |
| `MYSQL_DATABASE` | `mco` | nome do banco |
| `MYSQL_USER` | `mco` | usuário da aplicação |
| `MYSQL_PASSWORD` | `mco` | senha da aplicação |
| `MYSQL_ROOT_PASSWORD` | `root` | senha do root (criação do banco) |
| `APP_PORT` | `8501` | porta exposta da app Streamlit |
| `PERCENTUAL_MINIMO` | `90.0` | percentual mínimo de cumprimento para "ATENDEU" |

## Estrutura do projeto

```
.
├── app/
│   ├── Home.py                 # entry-point do Streamlit
│   ├── config.py               # carrega .env
│   ├── db.py                   # engine + session SQLAlchemy
│   ├── models.py               # modelos ORM (ParametroLinha, LoteImportacao, ViagemMCO)
│   ├── importer.py             # parser do CSV MCO
│   ├── consistency.py          # regras de classificação e queries
│   └── pages/
│       ├── 1_Parametros.py
│       ├── 2_Importar_MCO.py
│       ├── 3_Consistencia.py
│       └── 4_Dashboard.py
├── sql/
│   ├── init.sql                # schema inicial (roda na 1ª subida do volume)
│   └── migrations/
│       └── 001_add_full_columns.sql
├── samples/                    # pasta para CSVs de teste (não versionados)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Modelo de dados

Três tabelas principais:

- **`parametro_linha`** — extensão programada por `(codigo_externo, sublinha)`.
- **`lote_importacao`** — metadados de cada importação (arquivo, contagem, data).
- **`viagem_mco`** — todas as 43 colunas do CSV (identificação operadora/linha, veículo, equipamento, catracas, tarifas, passageiros, integração, etc.). Dedup garantida por `UNIQUE(viagem_id_externo)`.

## Fluxo de uso

1. **Parâmetros** — cadastre a extensão de cada `Linha + Sublinha` em metros.
2. **Importar MCO** — suba o CSV diário; linhas com `Viagem` ID já existente são ignoradas.
3. **Consistência** — escolha um lote, ajuste o % mínimo se necessário, filtre por status/linha/veículo, exporte o relatório em Excel.
4. **Dashboard** — visualize tendências por período, operadora, garagem e linha, com identificação rápida de veículos problemáticos.

## Migração de banco já existente

Se você atualizou o código mas já tem dados no banco (não quer recriar o volume), aplique a migração:

```bash
docker compose exec -T mysql mysql -uroot -proot mco < sql/migrations/001_add_full_columns.sql
```

Para reset completo em ambiente de desenvolvimento:

```bash
docker compose down -v
docker compose up -d --build
```

## Layout esperado do CSV MCO

Cabeçalho com **separador `;`** e **decimal `,`**, contendo (entre outras) as colunas:

`Código Operadora; Nome Operadora; Nome Garagem; Código Interno Linha; Código Externo Linha; Nome Linha; Num Terminal; Viagem; Código Veículo; Numero Veículo; Desc. Tipo Veículo; Código Equipamento; Numero de Série do Equipamento; Sub Linha; Data Hora Início Operação; Data Hora Final Operação; Cartão Motorista; Cartão Cobrador; Catraca Pendente; Catraca Inicial; Catraca Final; Distância; Viagem; Orgão Gestor; CMP TER SUB; Tipo Viagem; Data Hora Saída Terminal; Coleta Pendente; Passageiros; Inteiras; VT; VT Integração; Gratuidade; Passagens; Bilhete Unitário; Passagens Integração; Estudantes; EStudantes Integração; Intervalo Viagem; Terminal; Data Coleta; Tipo Data; Data Hora Início; Data Hora Inserção`

Observações:

- A coluna `Viagem` aparece duas vezes: a primeira é o tipo (`Nor.`/`Extra`), a segunda é o ID externo da viagem (usado para deduplicação).
- A coluna `Distância` deve estar em **metros**.
- Colunas obrigatórias mínimas para importação: `Código Externo Linha`, `Sub Linha`, `Distância`.
