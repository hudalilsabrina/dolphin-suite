"""
Dolphin AI (dphn.ai) Full Automated Harvester Engine.
Handles SIWE Login -> Telegram Bot Linking -> Coupon Redemption ($10) -> API Key Minting -> 9Router Ingestion.
"""

from __future__ import annotations

import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

import requests
from eth_account import Account
from eth_account.messages import encode_defunct
from pyrogram import Client

from src.router_sync import submit_dolphin_key_to_9router

logger = logging.getLogger("DolphinRedeemer")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")


class DolphinSession:
    def __init__(self, base_url: str = "https://v2.dphn.ai", timeout: int = 25, proxy: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": UA,
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/"
        })
        if proxy:
            self.session.proxies.update({"http": proxy, "https": proxy})
        self.csrf: str = ""

    def siwe_login(self, wallet: Dict[str, str]) -> str:
        """Executes Sign-In with Ethereum (SIWE) on Dolphin backend."""
        addr = wallet["address"]
        priv = wallet["private_key"]

        # 1. Request Challenge
        r = self.session.get(f"{self.base_url}/api/auth/challenge", params={"address": addr}, timeout=self.timeout)
        r.raise_for_status()
        d = r.json()
        msg = d.get("message")
        nonce = d.get("nonce")
        if not msg or not nonce:
            raise ValueError(f"Invalid challenge response: {d}")

        # 2. Sign message with Ethereum private key
        sig = Account.sign_message(encode_defunct(text=msg), private_key=priv).signature.hex()
        if not sig.startswith("0x"):
            sig = "0x" + sig

        # 3. Post verification
        v = self.session.post(
            f"{self.base_url}/api/auth/verify",
            json={"address": addr, "nonce": str(nonce), "signature": sig},
            timeout=self.timeout
        )
        if not v.ok:
            raise RuntimeError(f"SIWE verification failed ({v.status_code}): {v.text[:200]}")

        # 4. Extract CSRF Token
        self.csrf = (
            self.session.cookies.get("dolphin_csrf") or
            self.session.cookies.get("csrf_token") or
            v.headers.get("X-CSRF-Token") or
            v.headers.get("x-csrf-token") or
            ""
        )
        if not self.csrf:
            try:
                self.csrf = v.json().get("csrfToken") or ""
            except Exception:
                pass

        logger.info(f"SIWE Login Success for {addr[:10]}... | CSRF: {self.csrf[:10]}...")
        return self.csrf

    def get_auth_me(self) -> Dict[str, Any]:
        try:
            return self.session.get(f"{self.base_url}/api/auth/me", timeout=self.timeout).json()
        except Exception:
            return {}

    def get_telegram_status(self) -> Dict[str, Any]:
        try:
            return self.session.get(f"{self.base_url}/api/telegram/status", timeout=self.timeout).json()
        except Exception as e:
            return {"required": True, "verified": False, "error": str(e)}

    def request_telegram_link(self) -> Tuple[str, str]:
        """Requests Telegram deep link and returns (deep_link, payload)."""
        headers = {
            "Content-Type": "application/json",
            "X-CSRF-Token": self.csrf,
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/"
        }
        res = self.session.post(f"{self.base_url}/api/telegram/link", json={}, headers=headers, timeout=self.timeout)
        if not res.ok:
            raise RuntimeError(f"Failed to request telegram link ({res.status_code}): {res.text[:200]}")
        data = res.json()
        deep_link = data.get("deep_link", "")
        payload = deep_link.split("start=")[-1] if "start=" in deep_link else ""
        return deep_link, payload

    def get_balance(self) -> Dict[str, Any]:
        try:
            return self.session.get(f"{self.base_url}/api/credits", timeout=self.timeout).json()
        except Exception:
            return {}

    def redeem_coupon(self, code: str) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "X-CSRF-Token": self.csrf
        }
        res = self.session.post(f"{self.base_url}/api/credits", json={"code": code}, headers=headers, timeout=self.timeout)
        if not res.ok:
            raise RuntimeError(f"Redeem coupon failed ({res.status_code}): {res.text[:200]}")
        return res.json()

    def create_api_key(self, name: str = "hermes-dolphin") -> str:
        headers = {
            "Content-Type": "application/json",
            "X-CSRF-Token": self.csrf
        }
        res = self.session.post(f"{self.base_url}/api/keys", json={"name": name}, headers=headers, timeout=self.timeout)
        if not res.ok:
            raise RuntimeError(f"Create API key failed ({res.status_code}): {res.text[:200]}")
        key = res.json().get("key", "")
        return key


async def verify_telegram_via_pyrogram(
    session_name: str,
    workdir: str,
    bot_username: str,
    payload: str,
    api_id: int,
    api_hash: str
) -> Dict[str, Any]:
    """Connects Pyrogram client and sends /start <payload> to @DolphinNM_bot."""
    logger.info(f"Connecting Pyrogram session '{session_name}' in {workdir}...")
    async with Client(name=session_name, api_id=api_id, api_hash=api_hash, workdir=workdir, no_updates=True) as app:
        me = await app.get_me()
        user_info = f"@{me.username}" if me.username else (me.first_name or str(me.id))
        logger.info(f"Logged in as Telegram user: {user_info} (ID: {me.id})")

        start_cmd = f"/start {payload}"
        logger.info(f"Sending '{start_cmd[:20]}...' to @{bot_username}")
        await app.send_message(bot_username, start_cmd)
        await asyncio.sleep(4)

        bot_reply = ""
        try:
            async for m in app.get_chat_history(bot_username, limit=3):
                txt = (m.text or m.caption or "").replace("\n", " ")
                if txt and not txt.startswith("/start"):
                    bot_reply = txt
                    logger.info(f"Bot Reply: {bot_reply[:100]}...")
                    break
        except Exception:
            pass

        return {"user_id": me.id, "username": me.username, "reply": bot_reply}


def test_dolphin_inference(api_key: str, model: str = "deepseek-ai/DeepSeek-V4.1-Flash") -> Dict[str, Any]:
    """Tests live inference on https://lighthouse.dphn.ai/run/text-v/v1/chat/completions."""
    url = "https://lighthouse.dphn.ai/run/text-v/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Ping test! Say 'Dolphin OK'"}],
        "max_tokens": 15
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if r.ok:
            data = r.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"success": True, "status": r.status_code, "reply": content.strip()}
        else:
            return {"success": False, "status": r.status_code, "error": r.text[:150]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def process_single_account(
    session_name: str,
    workdir: str,
    config: Dict[str, Any],
    wallets_store: Dict[str, Any]
) -> Dict[str, Any]:
    """Executes the full pipeline for one Telegram session."""
    api_id = config.get("api_id")
    api_hash = config.get("api_hash")
    coupon_code = config.get("coupon_code", "API10")
    key_name = config.get("key_name", "hermes-dolphin")
    bot_user = config.get("bot_username", "DolphinNM_bot")
    poll_tries = config.get("poll_tries", 15)
    poll_delay = config.get("poll_delay", 3)

    # 1. Get or create Burner Wallet
    if session_name in wallets_store and wallets_store[session_name].get("private_key"):
        wallet = wallets_store[session_name]
        is_new_wallet = False
    else:
        acc = Account.create()
        wallet = {"address": acc.address, "private_key": acc.key.hex()}
        wallets_store[session_name] = wallet
        is_new_wallet = True

    logger.info(f"Wallet for session {session_name}: {wallet['address']} (New={is_new_wallet})")

    # 2. SIWE Login
    d_session = DolphinSession(base_url=config.get("base_url", "https://v2.dphn.ai"))
    d_session.siwe_login(wallet)

    # 3. Check Telegram Verification
    st = d_session.get_telegram_status()
    if not st.get("verified"):
        logger.info("Telegram not verified. Requesting deep link...")
        deep_link, payload = d_session.request_telegram_link()
        logger.info(f"Deep link payload: {payload[:15]}...")

        # Send /start payload via Pyrogram
        asyncio.run(verify_telegram_via_pyrogram(
            session_name=session_name,
            workdir=workdir,
            bot_username=bot_user,
            payload=payload,
            api_id=api_id,
            api_hash=api_hash
        ))

        # Poll status
        for attempt in range(1, poll_tries + 1):
            time.sleep(poll_delay)
            st = d_session.get_telegram_status()
            if st.get("verified"):
                logger.info(f"✅ Telegram verified successfully on attempt {attempt}!")
                break
        else:
            raise TimeoutError("Telegram verification timed out on Dolphin backend.")
    else:
        logger.info("✅ Telegram is already verified for this wallet.")

    # 4. Check initial balance
    initial_bal = d_session.get_balance()
    logger.info(f"Current Balance: ${initial_bal.get('balance_usd', '?')}")

    # 5. Redeem Coupon Code
    logger.info(f"Redeeming coupon code: {coupon_code}...")
    redeem_res = d_session.redeem_coupon(coupon_code)
    new_bal = redeem_res.get("new_balance_usd") or redeem_res.get("credit_amount_usd")
    logger.info(f"🎉 Coupon Redeemed! New balance: ${new_bal}")

    # 6. Create API Key
    logger.info(f"Creating API Key '{key_name}'...")
    api_key = d_session.create_api_key(name=key_name)
    logger.info(f"🔑 Minted API Key: {api_key[:16]}... (len: {len(api_key)})")

    # 7. Test Live Inference
    logger.info("Testing live inference on DeepSeek-V4.1-Flash...")
    inf_res = test_dolphin_inference(api_key, model=config.get("model", "deepseek-ai/DeepSeek-V4.1-Flash"))
    logger.info(f"Inference Result: {inf_res}")

    # 8. Auto-submit to 9Router
    if config.get("auto_submit_9router", True):
        router_ok = submit_dolphin_key_to_9router(
            api_key=api_key,
            name=f"Dolphin ({session_name})"
        )
        logger.info(f"9Router Ingestion Status: {router_ok}")

    # 9. Backup key to keys.txt
    keys_file = Path(config.get("keys_file", "data/keys.txt"))
    keys_file.parent.mkdir(parents=True, exist_ok=True)
    with open(keys_file, "a", encoding="utf-8") as f:
        f.write(f"{api_key}\n")

    return {
        "success": True,
        "session": session_name,
        "wallet": wallet["address"],
        "balance": new_bal,
        "api_key": api_key,
        "inference": inf_res
    }
