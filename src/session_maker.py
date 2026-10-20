"""
Interactive Telegram Session Generator for Pyrogram.
Allows quickly logging in accounts and creating .session files in sessions/ directory.
"""

from __future__ import annotations

import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import json
import os
import sys
from pathlib import Path
from pyrogram import Client

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"api_id": 2040, "api_hash": "b18441a1ff607e10a989891a5462e627"}


async def create_interactive_session():
    cfg = load_config()
    api_id = cfg.get("api_id")
    api_hash = cfg.get("api_hash")

    print("\n" + "=" * 60)
    print("   🐬 PYROGRAM TELEGRAM SESSION GENERATOR FOR DOLPHIN")
    print("=" * 60)

    name = input("\nMasukkan Nama Session (contoh: akun_1 atau nomor HP): ").strip()
    if not name:
        name = "tg_session"

    session_file = SESSIONS_DIR / f"{name}.session"
    if session_file.exists():
        print(f"[!] Warning: File {session_file} sudah ada!")
        c = input("Timpa session ini? (y/N): ").strip().lower()
        if c != "y":
            print("Dibatalkan.")
            return

    print(f"\n[*] Menginisialisasi Client untuk session: {name}")
    async with Client(name=name, api_id=api_id, api_hash=api_hash, workdir=str(SESSIONS_DIR)) as app:
        me = await app.get_me()
        print("\n" + "=" * 60)
        print(f" [✓] LOGIN BERHASIL!")
        print(f" • Nama      : {me.first_name} {me.last_name or ''}")
        print(f" • Username  : @{me.username or 'Tanpa Username'}")
        print(f" • User ID   : {me.id}")
        print(f" • File Path : {session_file}")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(create_interactive_session())
