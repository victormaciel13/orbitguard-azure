"""
OrbitGuard AI — Azure Functions (modelo Python v2)
===================================================

Duas funções no mesmo app:

1) ingest_orbital  — Timer trigger (a cada 15 min, equivalente ao
   EventBridge): simula a coleta de um tile de satélite, "classifica"
   a cobertura do solo (placeholder do modelo CNN da entrega de
   Computer Vision), calcula o risco e grava no Cosmos DB.

2) alerts          — HTTP trigger (rota GET /api/alerts): devolve os
   alertas mais recentes em JSON para o painel.

Boas práticas demonstradas:
- Configuração lida do Azure App Configuration (nunca hardcoded).
- Segredo (chave do provedor de dados) lido do Azure Key Vault.
- Acesso sem senha via Managed Identity (DefaultAzureCredential).
- Logs estruturados enviados ao Application Insights.
"""

import os
import json
import random
import logging
import datetime as dt

import azure.functions as func

# SDKs Azure (vêm no requirements.txt)
from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient, PartitionKey

app = func.FunctionApp()

# ---------------------------------------------------------------
# Configuração (lida de variáveis de ambiente / App Configuration)
# ---------------------------------------------------------------
COSMOS_URL = os.environ.get("COSMOS_URL", "")
COSMOS_DB = os.environ.get("COSMOS_DB", "orbitdb")
COSMOS_CONTAINER = os.environ.get("COSMOS_CONTAINER", "alerts")
KEYVAULT_URL = os.environ.get("KEYVAULT_URL", "")
RISK_THRESHOLD_HIGH = float(os.environ.get("RISK_THRESHOLD_HIGH", "0.85"))

CLASSES = [
    "AnnualCrop", "Forest", "HerbaceousVegetation", "Highway", "Industrial",
    "Pasture", "PermanentCrop", "Residential", "River", "SeaLake",
]

REGIOES = [
    ("Cerrado — MT", -13.2, -56.1),
    ("Vale do Itajaí — SC", -27.0, -49.1),
    ("Amazônia — PA", -3.4, -52.3),
    ("Pantanal — MS", -18.5, -56.6),
    ("Litoral — BA", -13.0, -38.5),
    ("Grande SP", -23.5, -46.6),
]

_credential = None
_cosmos_container = None


def get_credential():
    """Managed Identity em produção; credenciais locais em dev."""
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential


def get_container():
    """Conecta ao Cosmos DB usando Managed Identity (sem chave no código)."""
    global _cosmos_container
    if _cosmos_container is None and COSMOS_URL:
        client = CosmosClient(COSMOS_URL, credential=get_credential())
        db = client.create_database_if_not_exists(COSMOS_DB)
        _cosmos_container = db.create_container_if_not_exists(
            id=COSMOS_CONTAINER,
            partition_key=PartitionKey(path="/id"),
        )
    return _cosmos_container


def get_secret_api_key():
    """Lê a chave do provedor orbital do Key Vault (nunca logada)."""
    if not KEYVAULT_URL:
        return ""
    try:
        from azure.keyvault.secrets import SecretClient
        sc = SecretClient(vault_url=KEYVAULT_URL, credential=get_credential())
        return sc.get_secret("satellite-api-key").value
    except Exception as e:  # noqa: BLE001
        logging.warning("Segredo indisponível: %s", e)
        return ""


# ---------------------------------------------------------------
# Lógica de domínio
# ---------------------------------------------------------------
def classificar_e_pontuar():
    regiao, lat, lon = random.choice(REGIOES)
    classe = random.choice(CLASSES)
    conf = round(random.uniform(0.78, 0.99), 2)

    if classe in ("Pasture", "AnnualCrop") and conf >= RISK_THRESHOLD_HIGH:
        risco, tipo = "alto", "Foco de queimada"
    elif classe in ("River", "SeaLake") and conf >= 0.88:
        risco, tipo = "alto", "Risco de enchente"
    elif classe in ("HerbaceousVegetation", "Highway"):
        risco, tipo = "medio", "Solo seco / monitoramento"
    else:
        risco, tipo = "baixo", "Vegetação saudável"

    return {
        "regiao": regiao, "lat": lat, "lon": lon,
        "classe": classe, "conf": conf, "risco": risco, "tipo": tipo,
    }


# ---------------------------------------------------------------
# 1) Timer trigger — ingestão orbital a cada 15 min
# ---------------------------------------------------------------
@app.timer_trigger(schedule="0 */15 * * * *", arg_name="timer",
                   run_on_startup=False, use_monitor=True)
def ingest_orbital(timer: func.TimerRequest) -> None:
    _ = get_secret_api_key()  # valida acesso ao provedor (chave nunca logada)
    item = classificar_e_pontuar()
    now = dt.datetime.now(dt.timezone.utc)
    record = {
        "id": f"tile-{int(now.timestamp())}-{random.randint(100, 999)}",
        "timestamp": now.isoformat(),
        **item,
    }
    container = get_container()
    if container:
        container.upsert_item(record)
        logging.info("Alerta gravado: regiao=%s risco=%s classe=%s",
                     record["regiao"], record["risco"], record["classe"])
    else:
        logging.warning("Cosmos indisponível — alerta não persistido (modo dev).")


# ---------------------------------------------------------------
# 2) HTTP trigger — GET /api/alerts
# ---------------------------------------------------------------
@app.route(route="alerts", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def alerts(req: func.HttpRequest) -> func.HttpResponse:
    alerts_list = []
    container = get_container()
    if container:
        try:
            query = "SELECT * FROM c ORDER BY c.timestamp DESC OFFSET 0 LIMIT 12"
            alerts_list = list(container.query_items(
                query=query, enable_cross_partition_query=True))
        except Exception as e:  # noqa: BLE001
            logging.error("Erro ao consultar Cosmos: %s", e)

    body = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "count": len(alerts_list),
        "alerts": alerts_list,
    }
    return func.HttpResponse(
        json.dumps(body),
        mimetype="application/json",
        headers={"Cache-Control": "no-cache"},
    )
