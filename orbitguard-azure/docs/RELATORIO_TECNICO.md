# Relatório Técnico — OrbitGuard AI · Infraestrutura Cloud (Azure)

**FIAP · Global Solution 2026 · Cloud Computing**

| Equipe | RM |
|--------|----|
| Integrante 1 | RM XXXXX |
| Integrante 2 | RM XXXXX |
| Integrante 3 | RM XXXXX |
| Integrante 4 | RM XXXXX |
| Integrante 5 | RM XXXXX |

**Link da aplicação:** `https://__PREENCHER_APOS_DEPLOY__.azurestaticapps.net`
**Repositório:** `https://github.com/__OWNER__/orbitguard-azure`

---

## 1. Solução e conexão com a Indústria Espacial (15 pts)

### 1.1 Problema
Queimadas e enchentes evoluem em horas. Os dados de observação da Terra —
capturados por satélites — chegam dispersos, pesados e sem tratamento, atrasando
a resposta da defesa civil e do agronegócio.

### 1.2 Solução
O **OrbitGuard AI** é a camada cloud que fecha esse ciclo: ingere periodicamente
tiles de satélite, classifica a cobertura do solo por visão computacional
(reaproveitando o modelo CNN da entrega de *Applied Computer Vision*), calcula um
índice de risco ambiental e publica alertas em um painel acessível quase em tempo
real. A natureza orbital do dado de entrada e o objetivo de monitorar a Terra
estabelecem a conexão genuína com a **Indústria Espacial**.

### 1.3 ODS conectados
- **ODS 13 — Ação contra a mudança climática** (prioritário): monitorar queimadas
  e uso do solo gera dados para mitigar emissões e antecipar eventos extremos.
- **ODS 15 — Vida terrestre**: classificação de florestas e degradação apoia o
  combate ao desmatamento.
- **ODS 11 — Cidades sustentáveis**: alertas de enchente ampliam o tempo de
  resposta da defesa civil.

---

## 2. Infraestrutura Azure — aplicação web pública (20 pts)

A aplicação é um **painel** hospedado no **Azure Static Web Apps**, com URL pública
HTTPS (`*.azurestaticapps.net`) e CDN/TLS embutidos. O Static Web App hospeda, na
mesma origem, o frontend e a API (Azure Functions em `/api`), eliminando CORS.

O painel atende ao mínimo exigido:
- **Identidade do produto:** nome, propósito e equipe.
- **Problema + ODS:** seções dedicadas.
- **Funcionamento:** pipeline em 3 etapas + painel ao vivo consumindo `/api/alerts`.

> **Print sugerido:** painel aberto pela URL do Static Web App.

---

## 3. Pipeline CI/CD (25 pts)

Ao conectar o repositório GitHub na criação do Static Web App, o Azure **gera
automaticamente um workflow do GitHub Actions** (`.github/workflows/azure-static-web-apps-*.yml`)
e realiza o primeiro deploy. A partir daí, **todo push na branch `main`** dispara
um novo build do frontend e o deploy das Functions da pasta `/api`.

Decisões:
- Deploy disparado por **Git trigger** (push em `main`).
- O token de deploy fica em **Secret do GitHub** (gerado pelo Azure), sem chaves
  manuais expostas no código.

> **Print sugerido:** workflow verde em *Actions* + aba *Summary* do Static Web App.

---

## 4. Segurança (20 pts)

Equivalências às boas práticas da disciplina, no Azure:

- **Azure Key Vault** (≈ Secrets Manager + KMS): guarda a chave do provedor de
  dados orbitais e a chave de criptografia. A Function lê o segredo em runtime; o
  valor **nunca** aparece no código nem nos logs. Vault configurado com **RBAC**.
- **Azure App Configuration** (≈ Parameter Store): centraliza parâmetros
  (limiar de risco, cadência de varredura).
- **Managed Identity + RBAC** (≈ IAM Roles com least privilege): o Static Web App
  recebe uma identidade gerenciada do sistema; o acesso ao Key Vault e ao Cosmos é
  concedido por **role assignments específicos** (Key Vault Secrets User; Cosmos
  Data Contributor), sem senha ou connection string no código. No código usamos
  `DefaultAzureCredential`.

> **Print sugerido:** o segredo no Key Vault (valor oculto) e a aba IAM com o
> role assignment para a identidade gerenciada.

---

## 5. Monitoramento (10 pts)

- **Application Insights** (≈ CloudWatch): coleta logs, métricas e exceções das
  Functions automaticamente (instrumentação via `host.json` + chave nas settings).
- **Alertas** sobre falhas/exceptions da Function → e-mail.
- **Azure Cost Management → Budget** (≈ AWS Budgets): limite mensal (ex.: US$10)
  com alerta em 80% e 100%.

**Motivo das escolhas:** a Azure Function é o ponto único de falha funcional (gera
e serve os alertas), então suas falhas e latência são as métricas mais vigiadas. O
Budget protege o ambiente acadêmico contra custos inesperados.

> **Print sugerido:** painel do Application Insights e o Budget configurado.

---

## 6. Decisões de arquitetura

| Decisão | Justificativa |
|---------|---------------|
| **Static Web Apps** | Hospeda site + API com 1 deploy e CI/CD automático. |
| **Azure Functions (serverless)** | Escala com o volume orbital; custo ocioso zero. |
| **Timer trigger** | Simula a cadência real de varredura de satélite (15 min). |
| **Cosmos DB Serverless** | NoSQL barato, paga por uso. |
| **Managed Identity** | Acesso aos recursos sem credenciais estáticas. |
| **Key Vault com RBAC** | Segredos centralizados e auditáveis. |
| **Bicep (IaC)** | Infra versionada e reproduzível. |

---

## 7. Como reproduzir
Ver `README.md` (passo a passo pelo portal). Alternativa por código: `az deployment
group create` com `infra/main.bicep`.

---

## 8. Evidências (anexar prints)
1. Painel aberto pela URL do Static Web App.
2. Workflow do GitHub Actions concluído com sucesso.
3. Recursos no grupo `rg-orbitguard` (Static Web App, Functions, Cosmos, Key Vault, App Config).
4. Key Vault + role assignment da Managed Identity (segurança).
5. Application Insights + Budget (monitoramento).
