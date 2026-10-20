"""
9Router Sync Module for Dolphin AI (dphn.ai).
Ensures Dolphin AI provider node, custom models, and connection data match 9Router's exact schema.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("DolphinRouterSync")

DOLPHIN_NODE_ID = "openai-compatible-chat-dolphin"
DOLPHIN_PREFIX = "dphn"
DOLPHIN_BASE_URL = "https://lighthouse.dphn.ai/run/text-v/v1"
DOLPHIN_MODEL_ID = "deepseek-ai/DeepSeek-V4.1-Flash"


def get_9router_db_path() -> Path:
    candidates = [
        Path("/var/lib/9router/db/data.sqlite"),
        Path.home() / ".config" / "9router" / "db" / "data.sqlite",
        Path.home() / ".9router" / "db" / "data.sqlite",
    ]
    if sys.platform == "win32":
        appdata = os.getenv("APPDATA")
        if appdata:
            candidates.insert(0, Path(appdata) / "9router" / "db" / "data.sqlite")

    for p in candidates:
        if p.exists():
            return p
    return Path("/var/lib/9router/db/data.sqlite")


def ensure_dolphin_node_exists(conn: sqlite3.Connection) -> None:
    """Creates or updates Dolphin AI providerNode & custom model in 9Router."""
    cur = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    node_data = {
        "prefix": DOLPHIN_PREFIX,
        "apiType": "chat",
        "baseUrl": DOLPHIN_BASE_URL,
        "logo": ""
    }

    # 1. Upsert providerNodes
    cur.execute(
        """INSERT INTO providerNodes (id, type, name, data, createdAt, updatedAt)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
             type=excluded.type, name=excluded.name, data=excluded.data, updatedAt=excluded.updatedAt""",
        (DOLPHIN_NODE_ID, "openai-compatible", "Dolphin AI", json.dumps(node_data), now_iso, now_iso)
    )

    # 2. Register model in kv (customModels) so 9Router router engine knows about it
    model_kv = {
        "providerAlias": DOLPHIN_PREFIX,
        "id": DOLPHIN_MODEL_ID,
        "type": "llm",
        "name": DOLPHIN_MODEL_ID,
        "caps": {
            "vision": False,
            "reasoning": False,
            "thinkDeeper": False,
            "speedMode": False,
            "jsonGuard": False,
            "contextSqueezer": False
        }
    }
    kv_key = f"{DOLPHIN_PREFIX}|{DOLPHIN_MODEL_ID}|llm"
    cur.execute(
        """INSERT INTO kv (scope, key, value)
           VALUES (?, ?, ?)
           ON CONFLICT(scope, key) DO UPDATE SET value=excluded.value""",
        ("customModels", kv_key, json.dumps(model_kv))
    )

    conn.commit()
    logger.info("Ensured Dolphin AI providerNode & customModel in 9Router.")


def submit_dolphin_key_to_9router(
    api_key: str,
    name: str = "Dolphin Key",
    db_path: Optional[Path | str] = None
) -> bool:
    """Inserts a Dolphin API key into 9Router providerConnections."""
    target_path = Path(db_path) if db_path else get_9router_db_path()
    if not target_path.exists():
        logger.warning(f"9Router SQLite DB not found at {target_path}")
        return False

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    conn_data = {
        "defaultModel": f"{DOLPHIN_PREFIX}/{DOLPHIN_MODEL_ID}",
        "apiKey": api_key,
        "testStatus": "active",
        "providerSpecificData": {
            "prefix": DOLPHIN_PREFIX,
            "apiType": "chat",
            "baseUrl": DOLPHIN_BASE_URL,
            "nodeName": "Dolphin AI",
            "connectionProxyEnabled": False,
            "connectionProxyUrl": "",
            "connectionNoProxy": ""
        },
        "lastError": None,
        "lastErrorAt": None,
        "errorCode": None,
        "backoffLevel": 0
    }

    try:
        conn = sqlite3.connect(str(target_path), timeout=25.0)
        ensure_dolphin_node_exists(conn)

        cur = conn.cursor()
        cur.execute(
            "SELECT id, data FROM providerConnections WHERE provider = ?",
            (DOLPHIN_NODE_ID,)
        )
        rows = cur.fetchall()
        matched_id = None
        for cid, d_str in rows:
            try:
                d = json.loads(d_str)
                if d.get("apiKey") == api_key:
                    matched_id = cid
                    break
            except Exception:
                pass

        if matched_id:
            cur.execute(
                "UPDATE providerConnections SET data = ?, updatedAt = ?, name = ? WHERE id = ?",
                (json.dumps(conn_data), now_iso, name, matched_id)
            )
            logger.info(f"Updated existing Dolphin connection: {name}")
        else:
            new_id = str(uuid.uuid4())
            cur.execute(
                """INSERT INTO providerConnections
                   (id, provider, authType, name, priority, isActive, data, createdAt, updatedAt)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (new_id, DOLPHIN_NODE_ID, "apikey", name, 1, 1, json.dumps(conn_data), now_iso, now_iso)
            )
            cur.execute("SELECT COUNT(*) FROM providerConnections WHERE provider = ?", (DOLPHIN_NODE_ID,))
            total = cur.fetchone()[0]
            logger.info(f"Added Dolphin AI connection #{total} to 9Router: {name}")

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error submitting Dolphin key to 9Router: {e}")
        return False
