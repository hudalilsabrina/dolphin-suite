# 🐬 Dolphin AI (dphn.ai) Auto-Redeem & 9Router Harvester Suite
> **Promo API10 — $10 Free DeepSeek V4.1 Flash Credit per Account**  
> **Inference Engine: `https://lighthouse.dphn.ai/run/text-v/v1`**

Suite otomasi cerdas untuk memanen kredit gratis **$10 USD** dari Dolphin AI menggunakan burner wallet EVM murni dan sesi Telegram (Pyrogram). API Key yang berhasil dibuat akan otomatis disuntikkan ke **9Router** untuk melayani inferensi model frontier **DeepSeek V4.1 Flash** dengan harga pasar termurah ($0.01 / $0.07 per 1M tokens, 97%+ cache hit rate).

---

## 🎯 Alur Kerja Sistem (Pipeline Flow)

```
[Burner EVM Wallet] 
       │  (Auto Generate via eth-account, Tanpa Gas Fee)
       ▼
[SIWE Auth @ v2.dphn.ai] 
       │  (Challenge Nonce & EIP-191 Signature Verification)
       ▼
[Telegram Link Request] 
       │  (Ambil Payload Deep Link @DolphinNM_bot)
       ▼
[Pyrogram Client Auto-Verify] 
       │  (Kirim /start <payload> ke Bot Telegram Dolphin)
       ▼
[Redeem Coupon Code: API10] 
       │  (Klaim Saldo Promo $10 USD)
       ▼
[Mint API Key] 
       │  (POST /api/keys -> dphn_live_...)
       ▼
[Live Inference Test & 9Router Ingestion] 
       │  (Test DeepSeek-V4.1-Flash & Inject ke SQLite 9Router)
       ▼
[Siap Pakai untuk Coding Agent & Inferensi di Port 20127!]
```

---

## 🚀 Fitur Unggulan

1. **Burner EVM Wallet Otomatis**:
   - Menghasilkan private key & address Ethereum baru secara instan menggunakan standard library `eth-account`.
   - Mengikuti standar **SIWE (Sign-In with Ethereum)** tanpa memerlukan saldo gas fee sedikit pun.
   - Dompet otomatis disimpan di `data/dolphin_wallets.json` untuk keperluan audit / reuse.

2. **Otomasi Verifikasi Telegram (Pyrogram)**:
   - Menghubungkan sesi Telegram `.session` yang tersimpan di folder `sessions/`.
   - Meminta tiket otorisasi unik dari endpoint `/api/telegram/link`.
   - Mengirimkan perintah `/start <payload>` ke bot resmi `@DolphinNM_bot` dan memantau status verifikasi secara otomatis.

3. **Auto-Redeem $10 USD (`API10`)**:
   - Memanggil `/api/credits` dengan kode kupon `API10`.
   - Menambahkan saldo promo $10 USD (cukup untuk **100+ Juta Tokens** DeepSeek V4.1 Flash).

4. **Pembuatan API Key & Uji Inferensi Langsung**:
   - Menghasilkan token API resmi via `/api/keys`.
   - Menjalankan uji ping ke gateway inferensi Lighthouse (`https://lighthouse.dphn.ai/run/text-v/v1/chat/completions`) untuk memastikan key aktif.

5. **Auto-Submit ke 9Router**:
   - Otomatis mendaftarkan node `openai-compatible-chat-dolphin` di database SQLite 9Router (`/var/lib/9router/db/data.sqlite`).
   - Kunci yang dipanen langsung berstatus `active` dan siap digunakan dengan model:
     - `dphn/deepseek-ai/DeepSeek-V4.1-Flash`

6. **Batch & Multi-Account Farming**:
   - Mendukung banyak sesi Telegram sekaligus. Cukup taruh file `.session` ke dalam folder `sessions/`, jalankan script, dan bot akan memproses satu per satu dengan jeda aman.

---

## 📦 Panduan Penggunaan Cepat

### 1. Buat Sesi Telegram (Pyrogram)
Jalankan script generator sesi interaktif:

```bash
# Di Linux / VPS:
python3 src/session_maker.py

# Di Windows:
Double-click '1_Login_Telegram.bat'
```
- Masukkan nama sesi (contoh: `akun_1` atau nomor telepon).
- Masukkan kode OTP Telegram yang dikirim ke aplikasi Telegram Anda.
- File `.session` akan otomatis tersimpan di folder `sessions/`.

*(Jika Anda sudah memiliki kumpulan file `.session` Pyrogram dari tempat lain, cukup copy semuanya langsung ke dalam folder `sessions/`).*

---

### 2. Jalankan Farming & Auto-Submit

```bash
# Di Linux / VPS:
python3 main.py --code API10

# Di Windows:
Double-click '2_Run_Farm.bat'
```

Bot akan otomatis:
1. Membaca semua file `.session` di folder `sessions/`.
2. Membuat burner wallet baru untuk tiap akun.
3. Melakukan SIWE login.
4. Meminta deep link dan mengirim `/start` ke `@DolphinNM_bot`.
5. Mengklaim kupon `API10` (+$10 USD).
6. Menghasilkan API key.
7. Menguji inferensi DeepSeek V4.1 Flash.
8. Menyuntikkan API key ke 9Router!

---

### 3. Konfigurasi (`config.json`)

```json
{
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
  "auto_submit_9router": true
}
```

---

## 📂 Struktur Direktori Proyek

```
dolphin-suite/
├── config.json                     # Konfigurasi API Telegram, Kupon, & Endpoint
├── requirements.txt                # Dependensi (eth-account, pyrogram, requests)
├── 1_Login_Telegram.bat            # Script login akun Telegram di Windows (1-click)
├── 2_Run_Farm.bat                  # Script eksekusi farming di Windows (1-click)
├── setup.sh                        # Installer dependensi Linux
├── run.sh                          # Runner Linux
├── main.py                         # CLI Runner utama
├── sessions/                       # Folder penyimpan file *.session Pyrogram
│   └── (letakkan file session di sini)
├── data/                           # Folder output & database lokal
│   ├── keys.txt                    # Kumpulan API key yang berhasil dipanen
│   ├── dolphin_wallets.json        # Database private key wallet EVM
│   └── dolphin_results.json        # Riwayat eksekusi lengkap
└── src/
    ├── redeemer.py                 # Core engine SIWE, TG linking, & redeem
    ├── router_sync.py              # Injektor ke SQLite 9Router
    └── session_maker.py            # Generator sesi Pyrogram interaktif
```

---

## ⚡ Verifikasi Mandiri API Key
Untuk menguji API key Dolphin secara manual:

```bash
curl https://lighthouse.dphn.ai/run/text-v/v1/chat/completions \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-ai/DeepSeek-V4.1-Flash",
    "messages": [{ "role": "user", "content": "Hello Dolphin!" }]
  }'
```
Atau via CLI:
```bash
python3 main.py --test-key <API_KEY>
```
