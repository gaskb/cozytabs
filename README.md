# 🎸 CozyTabs

*[Italiano sotto / Italian below](#cozytabs-italiano)*

[![Version](https://img.shields.io/badge/version-1.4.1-blue.svg)](https://github.com/gaskb/cozytabs)
[![License: GPLv3](https://img.shields.io/badge/license-GPLv3-orange.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-multi--arch-blue.svg)](https://hub.docker.com/r/gaskb/cozytabs)

A personal Telegram bot that transforms guitar lesson videos and reels (TikTok, Instagram Reels, YouTube Shorts) into complete, structured study sheets directly in **Notion**, formatted for music stands or tablets, complete with 6-string ASCII tablature, chord boxes, fingerings, and technical tips.

---

## 🎯 The Problem Solved

We often discover inspiring guitar riffs, licks, or lessons on social media when away from our instruments (e.g., lounging on the couch or on a break). When we finally pick up the guitar, social platforms are the worst possible practice environment:
* 30-second vertical videos looping continuously without pause.
* Text overlays, captions, and UI buttons blocking the fretboard.
* No way to loop specific bars or slow down difficult passages cleanly.
* Absence of a readable score or tablature to follow at your own pace.

**CozyTabs** eliminates this friction: simply share the video link to your private Telegram bot from your phone. Behind the scenes, the bot downloads the media, uses **Gemini's multimodal analysis (audio + video)** to dissect both sound and visual frames, and compiles a comprehensive study page into your Notion Database.

---

## 🏗️ Architecture

```text
[TikTok / Reels / Shorts] ──(Share via Telegram)──> [CozyTabs Bot]
                                                            │
                                              ┌─────────────┴─────────────┐
                                              ▼                           ▼
                                          [yt-dlp]                [Gemini Multimodal]
                                    (Clean .mp4 / audio)       (Vision OCR + Audio 16kHz)
                                              │                           │
                                              └─────────────┬─────────────┘
                                                            ▼
                                                 [Notion Study Database]
                                              - Properties: Key, Tuning, Chords
                                              - 6-String ASCII Tablature
                                              - Chord Fingerings & Boxes
                                              - Strumming & Right-hand Advice
```

---

## 🚀 Key Features

* **Zero Friction from Mobile**: Share any TikTok/Reels link to your bot via the native share sheet and put your phone down.
* **Dual Multimodal AI (Audio + Vision)**: Combines listening to the audio track (16kHz mono to identify exact musical key, tempo, chord changes, and strumming rhythm) with visual frame analysis (OCR of on-screen tabs and fretboard fingering tracking).
* **Structured Notion Database**: Stores cards in a designated Notion Database with typed properties (*Title*, *Author*, *Key*, *Tuning*, *Capo*, *Chords*, *Format*, *Source Link*, *Date*) and video thumbnail cover.
* **Photo Mode & Educational Infographics**: Seamlessly analyzes image carousels and static chord chart slides in addition to videos.
* **Automatic Tab Error Correction**: Cross-references on-screen tablature against observed finger positions and auditory harmony, correcting typos made in video captions.
* **Security & Whitelisting**: Strictly restricts bot interactions to authorized Telegram User IDs (`ALLOWED_USER_IDS`).
* **Containerized & Resilient**: Hardened Docker deployment with non-root execution, native `HEALTHCHECK`, concurrency semaphore, and 100% decoupled unit test suite.

---

## ⚙️ Configuration (.env)

Copy `.env.example` to `.env` and fill in your credentials:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
ALLOWED_USER_IDS=12345678,87654321
GEMINI_API_KEY=your_gemini_api_key_here
NOTION_TOKEN=your_notion_integration_token_here
NOTION_PARENT_PAGE_ID=your_parent_page_id_here
NOTION_DATABASE_ID=your_notion_database_id_here  # Optional: publishes directly to database
DOWNLOAD_DIR=/tmp/cozytabs
LOG_LEVEL=INFO
```

---

## 🐳 Running with Docker

```bash
docker compose pull
docker compose up -d
```

Or build locally:

```bash
docker build -t cozytabs:latest .
docker run -d --name cozytabs --env-file .env cozytabs:latest
```

---

## 🧪 Automated Tests

The test suite thoroughly validates configuration parsing, access whitelist, URL extraction, Pydantic structured output models, multimodal audio processing, and Notion API integration:

```bash
pytest -v
```

---

## 📜 License

Released under the [GNU GPLv3](LICENSE) license.

CozyTabs is free and open-source. If you find it helpful for your guitar practice, feel free to [buy me a coffee on Ko-fi](https://ko-fi.com/gaskb) ☕!

---

<br>

<a name="cozytabs-italiano"></a>
# 🎸 CozyTabs (Italiano)

Bot Telegram personale (`@cozytabs_bot`) che trasforma i video di chitarra (TikTok, Instagram Reels, YouTube Shorts) in schede di studio complete su **Notion**, pronte per il leggio o tablet, con tablatura ASCII, accordi, diteggiature e spiegazione della tecnica.

---

## 🎯 Il Problema Risolto

Spesso scopriamo riff o lezioni di chitarra interessanti su TikTok mentre siamo lontani dallo strumento (es. sul divano o in pausa). Quando poi siamo alla postazione con la chitarra in braccio, le app social sono l'ambiente peggiore possibile per studiare:
* Video verticali che vanno in loop continuo da 30 secondi.
* Sovrimpressioni, testi e banner che coprono il manico.
* Impossibile rallentare a sezioni o mettere in loop battute specifiche.
* Mancanza di uno spartito o tablatura comoda da consultare.

**CozyTabs** risolve questo attrito: basta condividere il link al bot Telegram mentre sei al telefono. Dietro le quinte, il bot scarica il video, Gemini analizza fotogrammi e traccia audio (analisi bimodale), e crea una scheda strutturata nel Database di Notion.

---

## 🏗️ Architettura

```text
[TikTok / Reels / Shorts] ──(Condividi via Telegram)──> [CozyTabs Bot]
                                                                │
                                                  ┌─────────────┴─────────────┐
                                                  ▼                           ▼
                                              [yt-dlp]                [Gemini Bimodale]
                                        (Download .mp4 pulito)    (Vision OCR + Audio 16kHz)
                                                  │                           │
                                                  └─────────────┬─────────────┘
                                                                ▼
                                                   [Notion Database CozyTabs]
                                                  - Proprietà: Tonalità, Accordi, Cover
                                                  - Tablatura ASCII a 6 corde
                                                  - Box accordi e diteggiature
                                                  - Mano destra e consigli studio
```

---

## 🚀 Funzionalità

* **Friction-Zero dal Telefono**: Condividi il link TikTok/Reels al bot Telegram e riponi il telefono.
* **Analisi Bimodale Gemini (Audio + Vision)**: Unisce l'ascolto della traccia audio (16kHz mono per rilevare tonalità reale, cambi accordo, tempo e strumming pattern) alla visione dei fotogrammi (OCR tab e diteggiatura sul manico).
* **Database Notion Strutturato**: Archivia le schede in un Database Notion con proprietà tipizzate (*Titolo*, *Autore*, *Tonalità*, *Accordatura*, *Capotasto*, *Accordi*, *Formato*, *Link Originale*, *Data*) e copertina thumbnail del video.
* **Supporto Photo Mode & Infografiche**: Analizza caroselli di immagini didattiche oltre ai normali video.
* **Correzione Refusi Video**: Riconosce eventuali errori nelle grafiche del video confrontandole con le posizioni reali delle dita e l'armonia percepita a orecchio.
* **Sicurezza & Whitelist**: Risponde solo agli utenti autorizzati (`ALLOWED_USER_IDS`).
* **Containerizzato & Resiliente**: Esecuzione rootless su Docker, `HEALTHCHECK` nativo, semaforo di concorrenza e test unitari disaccoppiati.

---

## ⚙️ Configurazione (.env)

Copia `.env.example` in `.env` e imposta le tue chiavi:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
ALLOWED_USER_IDS=12345678,87654321
GEMINI_API_KEY=your_gemini_api_key_here
NOTION_TOKEN=your_notion_integration_token_here
NOTION_PARENT_PAGE_ID=your_parent_page_id_here
NOTION_DATABASE_ID=your_notion_database_id_here  # Opzionale: pubblica direttamente nel database
DOWNLOAD_DIR=/tmp/cozytabs
LOG_LEVEL=INFO
```

---

## 🐳 Esecuzione con Docker

```bash
docker compose pull
docker compose up -d
```

---

## 🧪 Test Automatici

I test unitari coprono la validazione di configurazione, whitelist, estrazione URL, parsing Pydantic, estrazione audio bimodale e client Notion Database:

```bash
pytest -v
```

---

## 📜 Licenza

Rilasciato sotto licenza [GNU GPLv3](LICENSE).

CozyTabs è gratuito e open-source. Se ti torna utile per i tuoi studi di chitarra, sentiti libero di [offrirmi un caffè su Ko-fi](https://ko-fi.com/gaskb) ☕!
