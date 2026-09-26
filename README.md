# 🎸 CozyTabs

![Version](https://img.shields.io/badge/version-1.1.1-blue.svg)
![API Version](https://img.shields.io/badge/api-1.1.1-green.svg)
![License](https://img.shields.io/badge/license-GPLv3-orange.svg)
![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)
![Docker](https://img.shields.io/badge/docker-multi--arch-blue.svg)

Bot Telegram personale (`@cozytabs_bot`) che trasforma i video di chitarra (TikTok, Instagram Reels, YouTube Shorts) in schede di studio complete su **Notion**, pronte per il leggio o tablet, con tablatura ASCII, accordi, diteggiature e spiegazione della tecnica.

---

## 🎯 Il Problema Risolto

Spesso scopriamo riff o lezioni di chitarra interessanti su TikTok mentre siamo lontani dallo strumento (es. sul divano o in pausa). Quando poi siamo alla postazione con la chitarra in braccio, TikTok è l'ambiente peggiore possibile:
* Video verticali che vanno in loop continuo da 30 secondi.
* Sovrimpressioni, testi e banner che coprono il manico.
* Impossibile rallentare a sezioni o mettere in loop battute specifiche.
* Mancanza di uno spartito o tablatura comoda da consultare.

**CozyTabs** risolve questo attrito: basta condividere il link al bot Telegram mentre sei al telefono. Dietro le quinte, il bot scarica il video, Gemini analizza i fotogrammi e l'armonia, e crea una scheda chiara su Notion.

---

## 🏗️ Architettura

```
[TikTok / Reels] ──(Condividi via Telegram)──> [CozyTabs Bot (@cozytabs_bot)]
                                                        │
                                          ┌─────────────┴─────────────┐
                                          ▼                           ▼
                                      [yt-dlp]                [Gemini Flash]
                               (Download .mp4 pulito)    (Vision OCR + Diteggiature)
                                          │                           │
                                          └─────────────┬─────────────┘
                                                        ▼
                                            [Scheda Notion Automatica]
                                         - Tablatura ASCII a 6 corde
                                         - Box accordi e diteggiature
                                         - Mano destra e consigli studio
```

---

## 🚀 Funzionalità

* **Friction-Zero dal Telefono**: Condividi il link TikTok/Reels al bot Telegram e riponi il telefono.
* **Analisi Multimodale Gemini**: Legge la grafica a schermo (accordi, tab sovraimpresse) e osserva le posizioni delle mani del chitarrista sul manico.
* **Correzione Refusi Video**: Riconosce eventuali errori nelle grafiche del video confrontandole con le posizioni reali delle dita.
* **Organizzazione su Notion**: Genera una sottopagina dedicata sotto `🎸 CozyTabs — Riff & Accordi`, con accordatura, tonalità, diteggiature esatte (`E A D G B e`) e codice ASCII ingrandibile.
* **Sicurezza & Whitelist**: Risponde solo agli utenti autorizzati (`ALLOWED_USER_IDS`).

---

## ⚙️ Configurazione (.env)

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
ALLOWED_USER_IDS=12345678
GEMINI_API_KEY=your_gemini_api_key_here
NOTION_TOKEN=your_notion_integration_token_here
NOTION_PARENT_PAGE_ID=your_parent_page_id_here
DOWNLOAD_DIR=/tmp/cozytabs
LOG_LEVEL=INFO
```

---

## 🧪 Test Automatici

I test unitari coprono la validazione di configurazione, whitelist, estrazione URL, parsing Pydantic e client Notion:

```bash
pytest -v
```

---

## 🐳 Deploy Docker (Homelab)

Il bot è containerizzato per l'homelab (`user@homelab:/dati/docker/cozytabs`):

```bash
# Avvio locale / homelab
docker compose pull
docker compose up -d
```

---

## 📜 Licenza

Rilasciato sotto licenza [GNU GPLv3](LICENSE).
Sviluppato con passione per l'ecosistema Homelab di Gas (`example.com`).
