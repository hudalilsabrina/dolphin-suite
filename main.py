"""
Main CLI Runner for Dolphin AI (dphn.ai) Auto-Redeem & Harvester Suite.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# Enable Windows ANSI colors
if sys.platform == "win32":
    os.system('color')

import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
SESSIONS_DIR = BASE_DIR / "sessions"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

from src.redeemer import process_single_account, test_dolphin_inference
from src.router_sync import submit_dolphin_key_to_9router, get_9router_db_path

# Palette Warna ANSI
G = "\033[92m"   # Hijau
R = "\033[91m"   # Merah
Y = "\033[93m"   # Kuning
C = "\033[96m"   # Cyan
M = "\033[95m"   # Magenta
W = "\033[97m"   # Putih
DIM = "\033[2m"  # Redup
B = "\033[1m"    # Tebal
X = "\033[0m"    # Reset


def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format=f"{DIM}%(asctime)s{X} [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )


def load_config() -> dict:
    default_cfg = {
        "api_id": 2040,
        "api_hash": "b18441a1ff607e10a989891a5462e627",
        "coupon_code": "API10",
        "key_name": "hermes-dolphin",
        "sessions_dir": "sessions",
        "wallets_file": "data/dolphin_wallets.json",
        "results_file": "data/dolphin_results.json",
        "keys_file": "data/keys.txt",
        "base_url": "https://v2.dphn.ai",
        "inference_url": "https://lighthouse.dphn.ai/run/text-v/v1",
        "model": "deepseek-ai/DeepSeek-V4.1-Flash",
        "bot_username": "DolphinNM_bot",
        "poll_tries": 15,
        "poll_delay": 3,
        "auto_submit_9router": True
    }
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                default_cfg.update(json.load(f))
        except Exception:
            pass
    return default_cfg


def load_wallets(path_str: str) -> dict:
    p = Path(path_str)
    if not p.is_absolute():
        p = BASE_DIR / p
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_wallets(path_str: str, data: dict):
    p = Path(path_str)
    if not p.is_absolute():
        p = BASE_DIR / p
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def print_banner(code: str, total_sessions: int):
    banner = f"""
{C}{'═'*64}{X}
 {B}{C}  🐬 DOLPHIN AI (DPHN.AI) PROMO HARVESTER & 9ROUTER SUITE 🐬{X}
{C}{'═'*64}{X}
  {DIM}Promo Code  :{X} {M}{B}{code}{X} ($10 Free DeepSeek V4.1 Flash Credit)
  {DIM}Target Pool :{X} {Y}{B}{total_sessions}{X} {W}Telegram sessions detected{X}
  {DIM}Inference   :{X} {G}https://lighthouse.dphn.ai/run/text-v/v1{X}
  {DIM}9Router DB  :{X} {W}{get_9router_db_path()}{X}
{C}{'─'*64}{X}
"""
    print(banner, flush=True)


def find_session_files(sessions_dir: Path) -> list[tuple[str, str]]:
    if not sessions_dir.exists():
        return []
    res = []
    for f in sorted(sessions_dir.glob("*.session")):
        res.append((f.stem, str(sessions_dir)))
    return res


def main():
    setup_logger()
    cfg = load_config()

    parser = argparse.ArgumentParser(description="Dolphin AI Harvester & 9Router Auto-Submit")
    parser.add_argument("--code", default=None, help="Coupon code (default from config: API10)")
    parser.add_argument("--session", nargs="*", default=None, help="Specific session name(s) to process")
    parser.add_argument("--sessions-dir", default=None, help="Sessions directory path")
    parser.add_argument("--api-id", type=int, default=None, help="Telegram API ID")
    parser.add_argument("--api-hash", type=str, default=None, help="Telegram API Hash")
    parser.add_argument("--key-name", default=None, help="API Key name to create")
    parser.add_argument("--test-key", type=str, default=None, help="Directly test an API key on Lighthouse inference")

    args = parser.parse_args()

    if args.test_key:
        print(f"\n[*] Testing inference with key: {args.test_key[:16]}...")
        res = test_dolphin_inference(args.test_key, model=cfg.get("model", "deepseek-ai/DeepSeek-V4.1-Flash"))
        print(f"[✓] Result: {json.dumps(res, indent=2)}\n")
        return

    if args.code:
        cfg["coupon_code"] = args.code
    if args.api_id:
        cfg["api_id"] = args.api_id
    if args.api_hash:
        cfg["api_hash"] = args.api_hash
    if args.key_name:
        cfg["key_name"] = args.key_name

    sessions_path = Path(args.sessions_dir) if args.sessions_dir else (BASE_DIR / cfg.get("sessions_dir", "sessions"))
    sessions_path.mkdir(parents=True, exist_ok=True)

    if args.session:
        session_list = [(s, str(sessions_path)) for s in args.session]
    else:
        session_list = find_session_files(sessions_path)

    print_banner(cfg["coupon_code"], len(session_list))

    if not session_list:
        print(f"{Y}[!] Belum ada file session yang ditemukan di folder '{sessions_path}'!{X}")
        print(f"👉 Jalankan: {W}python3 src/session_maker.py{X} untuk login Telegram baru.")
        print(f"👉 Atau copy file {W}<nama>.session{X} Pyrogram Anda ke folder {W}sessions/{X}.\n")
        sys.exit(0)

    wallets_store = load_wallets(cfg.get("wallets_file", "data/dolphin_wallets.json"))
    results = []

    for idx, (s_name, s_dir) in enumerate(session_list, 1):
        print(f"{C}{'─'*64}{X}")
        print(f"  {B}{C}[AKUN {idx}/{len(session_list)}]{X} {Y}Target Session:{X} {W}{B}{s_name}{X}")
        print(f"{C}{'─'*64}{X}")

        try:
            res = process_single_account(s_name, s_dir, cfg, wallets_store)
            results.append(res)
            print(f"  {G}{B}✓ SUKSES!{X} API Key: {G}{res['api_key'][:25]}...{X} | Saldo: ${res['balance']}")
        except Exception as e:
            print(f"  {R}{B}✗ GAGAL:{X} {e}")
            results.append({"success": False, "session": s_name, "error": str(e)})
        finally:
            save_wallets(cfg.get("wallets_file", "data/dolphin_wallets.json"), wallets_store)

        if idx < len(session_list):
            time.sleep(3)

    # Save results
    results_path = BASE_DIR / cfg.get("results_file", "data/dolphin_results.json")
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    ok_count = sum(1 for r in results if r.get("success"))
    print(f"\n{C}{'═'*64}{X}")
    print(f"  {B}{C}📊 RINGKASAN FARMING DOLPHIN AI 📊{X}")
    print(f"{C}{'═'*64}{X}")
    print(f"  Total Berhasil : {G}{B}{ok_count}{X}/{len(session_list)} akun")
    print(f"  Kumpulan Key   : {W}{cfg.get('keys_file')}{X}")
    print(f"  Riwayat Akun   : {W}{cfg.get('results_file')}{X}")
    print(f"{C}{'═'*64}{X}\n")


if __name__ == "__main__":
    main()
