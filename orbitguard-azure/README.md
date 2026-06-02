# 🛰️ OrbitGuard AI — Infraestrutura Cloud (Azure)

> **FIAP · Global Solution 2026 · Cloud Computing**
> Solução de cloud computing conectada à Indústria Espacial.

O **OrbitGuard AI** é uma plataforma de monitoramento ambiental baseada em dados
espaciais, IA e visão computacional. Esta entrega implementa a **infraestrutura
cloud no Microsoft Azure**: ingestão de dados orbitais, processamento serverless,
painel público, segurança, CI/CD e monitoramento.

---

## 👥 Equipe

| Nome | RM |
|------|----|
| Integrante 1 | RM XXXXX |
| Integrante 2 | RM XXXXX |
| Integrante 3 | RM XXXXX |
| Integrante 4 | RM XXXXX |
| Integrante 5 | RM XXXXX |

---

## 🗺️ Arquitetura

```
   Push na branch main  ┌──────────────────────────────────────────┐
   ───────────────────► │     GitHub Actions (gerado pelo SWA)       │
                        │  build do /frontend + deploy do /api        │
                        └───────────────┬─────────────────────────────┘
                                        ▼
   ┌─────────┐   HTTPS   ┌────────────────────────────────┐
   │ Usuário │ ────────► │   Azure Static Web App           │
   └─────────┘           │  ┌────────────┐  ┌────────────┐  │
                         │  │  Frontend  │  │  /api      │  │
                         │  │  (painel)  │─►│  Functions │  │
                         │  └────────────┘  └─────┬──────┘  │
                         └────────────────────────┼─────────┘
                                                  │ Managed Identity (sem senha)
                       ┌──────────────────────────┼───────────────────────────┐
                       ▼                           ▼                           ▼
                 ┌───────────┐             ┌─────────────┐           ┌──────────────────┐
                 │ Cosmos DB │             │  Key Vault  │           │ App Configuration│
                 │  (alerts) │             │  (segredo)  │           │   (parâmetros)   │
                 └───────────┘             └─────────────┘           └──────────────────┘
                       │
                       ▼
        Application Insights (logs, métricas, alertas) · Cost Management (Budget)

   Timer trigger (a cada 15 min) → ingest_orbital → classifica → grava no Cosmos
```

---

## 📂 Estrutura

```
orbitguard-azure/
├── frontend/                    # Painel → Static Web App
│   ├── index.html               #   identidade, problema, ODS, solução
│   ├── styles.css
│   ├── app.js                   #   consome /api/alerts
│   └── staticwebapp.config.json #   roteamento + runtime da API
├── api/                         # Azure Functions (backend)
│   ├── function_app.py          #   Timer (ingestão) + HTTP (/alerts)
│   ├── requirements.txt
│   ├── host.json
│   └── local.settings.json
├── infra/
│   └── main.bicep               # IaC: Cosmos, Key Vault, App Config, SWA, Insights, RBAC
├── .github/workflows/           # (gerado automaticamente pelo Static Web App)
└── docs/
    └── RELATORIO_TECNICO.md
```

---

## 🚀 Caminho recomendado: portal do Azure (passo a passo)

> Tira print de cada tela — você vai precisar para a documentação (10 pts).

### Passo 0 — Subir o código para o GitHub
Crie um repositório (ex.: `orbitguard-azure`) e faça push deste projeto.

### Passo 1 — Grupo de Recursos
Portal → **Criar um recurso** → busque **Resource group** → criar.
- Nome: `rg-orbitguard`
- Região: `East US 2` (boa cobertura do Static Web Apps)

### Passo 2 — Cosmos DB
**Criar recurso** → **Azure Cosmos DB** → **Azure Cosmos DB for NoSQL**.
- Grupo: `rg-orbitguard`
- Modo de capacidade: **Serverless** (mais barato)
- Depois de criado: **Data Explorer** → New Container → Database `orbitdb`, Container `alerts`, Partition key `/id`.

### Passo 3 — Key Vault
**Criar recurso** → **Key Vault**.
- Nome: `orbitguard-kv-SEUNUMERO`
- Modelo de permissão: **RBAC do Azure**
- Depois: **Secrets → Generate/Import** → nome `satellite-api-key`, valor `demo-key`.

### Passo 4 — App Configuration
**Criar recurso** → **App Configuration** (tier **Free**).
- Depois: **Configuration explorer** → criar chaves:
  - `risk_threshold_high` = `0.85`
  - `scan_interval_min` = `15`

### Passo 5 — Application Insights
**Criar recurso** → **Application Insights**.
- Nome: `orbitguard-insights` · Modo: Workspace-based.

### Passo 6 — Static Web App (site + API + CI/CD)  ⭐
**Criar recurso** → **Static Web App**.
- Nome: `orbitguard-site` · Plano: **Free**
- **Origem do deploy: GitHub** → autorize e selecione seu repositório/branch `main`.
- **Detalhes da build:**
  - Build Presets: **Custom**
  - App location: `/frontend`
  - Api location: `/api`
  - Output location: *(vazio)*
- Ao criar, o Azure **commita um workflow do GitHub Actions no seu repo** e dispara
  o primeiro deploy. **Isso já entrega o critério de CI/CD.**
- A URL pública sai em **Overview → URL** (ex.: `https://xxxx.azurestaticapps.net`).

### Passo 7 — Identidade Gerenciada + RBAC (Segurança)
1. No Static Web App → **Configuração → Identity** → **System assigned → On**.
2. No **Key Vault → Access control (IAM) → Add role assignment**:
   - Role: **Key Vault Secrets User**
   - Atribuir a: a identidade gerenciada do `orbitguard-site`.
3. No **Cosmos DB → Access control (IAM)** (ou via CLI para o role de dados):
   - Conceda leitura/escrita de dados à mesma identidade.

### Passo 8 — Configurar as variáveis da API
No Static Web App → **Configuração → Application settings**, adicione:
| Nome | Valor |
|------|-------|
| `COSMOS_URL` | endpoint do Cosmos (Overview do Cosmos) |
| `COSMOS_DB` | `orbitdb` |
| `COSMOS_CONTAINER` | `alerts` |
| `KEYVAULT_URL` | URI do Key Vault |
| `RISK_THRESHOLD_HIGH` | `0.85` |
| `APPINSIGHTS_INSTRUMENTATIONKEY` | chave do Application Insights |

### Passo 9 — Budget (Monitoramento de custo)
Portal → **Gerenciamento de custo + cobrança → Budgets → Add**.
- Escopo: `rg-orbitguard` · Valor: `10 USD/mês` · Alertas em 80% e 100%.

### Passo 10 — Alertas do Application Insights
Application Insights → **Alerts → Create** → métrica de **falhas/exceptions** da
Function → notificar por e-mail. (Justificativa no relatório.)

### Passo 11 — Validar
Abra a URL do Static Web App. O painel carrega; em até 15 min o Timer popula o
Cosmos e o painel passa de "modo demonstração" para "API online".

---

## 🧭 Mapa de pontuação (100 pts)

| Critério | Pts | Onde |
|----------|-----|------|
| Solução + conexão espacial + ODS | 15 | painel + relatório (ODS 13/15/11) |
| Infraestrutura (app pública) | 20 | Static Web App → URL `azurestaticapps.net` |
| Pipeline CI/CD | 25 | GitHub Actions gerado pelo SWA (trigger git push) |
| Segurança | 20 | Key Vault + App Config + Managed Identity + RBAC |
| Monitoramento | 10 | Application Insights + alertas + Budget |
| Documentação técnica | 10 | `docs/RELATORIO_TECNICO.md` |

---

## 💰 Custos
Static Web App Free, Cosmos Serverless, App Config Free → praticamente gratuito.
O Budget avisa antes de qualquer custo relevante. Para encerrar tudo após a
avaliação: **excluir o grupo de recursos `rg-orbitguard`**.
```bash
az group delete -n rg-orbitguard --yes
```
