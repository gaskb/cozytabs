# 🎸 CozyTabs — Audit di Conformità alle Best Practice Notion & Homelab

**Data Audit:** 26 Settembre 2026  
**Versione Progetto:** v1.3.0  
**Documento di Riferimento:** [Standard Architetturali Homelab & Backend](https://app.notion.com/p/Standard-Architetturali-Homelab-Backend-00000000000000000000000000000000) (Notion ID: `00000000-0000-0000-0000-000000000000`)  
**Codice Sorgente:** `/Users/gas/dev/gas/dev_projects/cozytabs` (GitLab: `github.com/gaskb/cozytabs`)

---

## 📊 Sintesi Esecutiva del Livello di Conformità

| Pilastro Linee Guida Notion | Stato Attuale | Valutazione |
| :--- | :---: | :--- |
| **1. Docker & Container Security** | 🟨 85% | Conforme per `.dockerignore` e utente rootless `appuser:1000`. **Manca `HEALTHCHECK` nativo nel Dockerfile**. |
| **2. Backend & Concurrency Patterns** | 🟩 100% | Pienamente conforme: `asyncio.to_thread` per I/O bloccante/CPU, Pydantic `BaseModel` tipizzato, semaforo di concorrenza. |
| **3. Sicurezza API & Gestione Credenziali** | 🟨 90% | Credenziali solo in header HTTP e whitelist `ALLOWED_USER_IDS`. **Migliorabile la sanitizzazione delle eccezioni in Telegram** (`str(e)` raw). |
| **4. Integrazione AI/LLM & Multimodalità** | 🟨 90% | Structured Outputs Pydantic nativi e multimodalità audio/video MP3 16kHz + Vision. **Manca timeout esplicito su client Gemini**. |
| **5. Resilienza UI & Telegram Bot** | 🟩 100% | Conforme: `ParseMode.HTML` con `html.escape()`, chunking 2000 caratteri Notion, throttling concorrenza a 2 task. |
| **6. Testing & CI Indipendente** | 🟨 80% | 20 test unitari, 100% disaccoppiati da `.env` locale. **Manca copertura formale degli Error Paths (timeout/4xx/5xx) e `.gitlab-ci.yml`**. |

**Punteggio Complessivo:** **90 / 100** (Livello: *Molto Alto / Production-Ready con Rifiniture Consigliate*)

---

## 🔍 Analisi Dettagliata per Ciascuna Area

### 1. Docker & Container Security per Homelab

#### ✅ Punti di Forza
- **`.dockerignore` configurato**: Esclude `.env`, `.env.*`, `cookies.txt`, cartelle `.git`, cache `venv/`, `__pycache__/`, `.pytest_cache/`, file multimediali e cartelle di runtime. Il contesto di build Docker è ridotto a sole poche decine di kilobyte (42 KB).
- **Container Rootless (Utente 1000)**: Il container non gira come `root`. Nel Dockerfile è presente l'utente non privilegiato `appuser` (UID 1000) proprietario di `/app` e `/tmp/cozytabs`. In caso di vulnerabilità o exploit in librerie C (es. decoder video FFmpeg o parser yt-dlp), l'host dell'homelab è protetto.

#### ⚠️ Aree di Miglioramento
1. **Assenza della direttiva `HEALTHCHECK` nel `Dockerfile`**:
   * *Regola Notion*: *"Ogni container web o demone deve dichiarare una direttiva HEALTHCHECK per permettere a Docker e Docker Compose di verificare lo stato effettivo dell'applicazione (non solo se il processo PID è vivo)"*.
   * *Soluzione proposta*: Trattandosi di un demone bot Telegram (senza porta TCP aperta), è possibile verificare periodicamente la presenza del processo Python o la freschezza di un file di heartbeat locale toccato dal polling loop:
     ```dockerfile
     HEALTHCHECK --interval=60s --timeout=5s --start-period=15s --retries=3 \
       CMD pgrep -f "python bot.py" > /dev/null || exit 1
     ```
2. **Perfezionamento `.dockerignore`**:
   * Aggiungere esplicitamente `*.pem`, `*.key`, `*.db` e `tests/` per evitare di includere nella release di produzione script di test o certificati accidentali.

---

### 2. Backend & Concurrency Patterns (Python & Asyncio)

#### ✅ Punti di Forza
- **Regola `async def` vs `def` rispettata**: Il bot usa `asyncio.to_thread()` per delegare qualsiasi computazione bloccante (`download_video`, `analyze_guitar_video`, `publish_to_notion`) a thread separati. Il dispatcher di Telegram non viene mai congelato, permettendo al bot di rispondere istantaneamente ad altri comandi o aggiornamenti.
- **Gestione della Concorrenza**: Presenza di `PROCESSING_SEMAPHORE = asyncio.Semaphore(2)` in `bot.py`, che limita l'elaborazione simultanea a massimo 2 video concorrenti, salvaguardando la RAM e i thread CPU del server Homelab durante le codifiche FFmpeg.
- **Validazione Pydantic**: Tutti i dati estratti (`GuitarLesson`, `Chord`) sono modellati con classi Pydantic tipizzate, documentate con `Field(description=...)` e valori di default sicuri.

---

### 3. Sicurezza API & Gestione Credenziali

#### ✅ Punti di Forza
- **Nessuna credenziale in URL**: Notion riceve il token esclusivamente tramite header HTTP `Authorization: Bearer <token>`, conforme alla best practice Zero-Trust.
- **Whitelist Utente Rigida**: Il bot verifica `Config.is_user_allowed(user.id)` all'ingresso di ogni comando e messaggio. Utenti non autorizzati vengono bloccati con notifica esplicita e loggati come warning con il loro user ID e username.

#### ⚠️ Aree di Miglioramento
1. **Sanitizzazione Eccezioni Telegram (`bot.py` riga 152)**:
   * *Codice attuale*: `safe_err_text = html.escape(str(e)[:300])`.
   * *Problema*: Sebbene vi sia l'escape HTML e il limite a 300 caratteri, `str(e)` può comunque esporre messaggi grezzi di librerie terze contenenti percorsi interni del filesystem (`/tmp/cozytabs/task_...`) o dettagli di rete dell'API Notion/Gemini.
   * *Soluzione proposta*: Mappare gli errori in categorie amichevoli per l'utente (es. *"Errore durante il download del video: verifica che il link sia pubblico"*, *"Errore durante l'elaborazione AI"*), mantenendo il dump completo dell'eccezione (`exc_info=True`) unicamente nei log interni del server.

---

### 4. Integrazione AI/LLM & Multimodalità

#### ✅ Punti di Forza
- **Structured Outputs Nativi**: Con la Milestone 2, `analyzer.py` genera lo schema JSON nativo (`GuitarLesson.model_json_schema()`) e lo passa via `response_format` all'SDK Gemini. Non ci sono regex fragili o parsing empirico di backtick markdown.
- **Multimodalità Bimodale Completa (Audio + Video)**: Con la Milestone 3, CozyTabs estrae l'audio a 16 kHz mono (MP3 compatto a 64 kbps) e lo invia assieme ai frame visivi. Gemini ascolta la tonalità, il tempo e lo strumming e li correla alle posizioni delle dita sul manico.

#### ⚠️ Aree di Miglioramento
1. **Timeout Esplicito sulle Chiamate Gemini (`analyzer.py`)**:
   * *Regola Notion*: *"Ogni richiesta verso API esterne, CDN o LLM deve includere un timeout esplicito (es. `timeout=30.0`). Mai invocare chiamate di rete senza limiti di attesa"*.
   * *Stato attuale*: Mentre `requests.get` (15s) e `requests.post` (20s) hanno timeout espliciti, la chiamata `client.interactions.create(...)` in `analyzer.py` usa il timeout socket di default del sistema.
   * *Soluzione proposta*: Passare `http_options={"timeout": 60.0}` all'inizializzazione del client `genai.Client(api_key=api_key, http_options={"timeout": 60.0})`.

---

### 5. Resilienza UI & Telegram Bot

#### ✅ Punti di Forza
- **Telegram `ParseMode.HTML`**: Nessun uso del Markdown v1 legacy di Telegram, eliminando i crash su caratteri riservati come underscore o parentesi quadre. Tutti i campi dinamici passano attraverso `html.escape()`.
- **Chunking Preventivo Notion**: Funzione `split_text_chunks(max_length=1900)` che spezza automaticamente blocchi di testo lunghi (es. spiegazioni armoniche o tablature complesse) per non violare il limite di 2000 caratteri per blocco imposto dalle API di Notion.
- **Preview Telegram Controllata**: La tablatura nel messaggio Telegram viene troncata a 800 caratteri con indicazione `\n...`, evitando di eccedere il limite globale del messaggio Telegram (4096 caratteri).

---

### 6. Testing & CI Indipendente

#### ✅ Punti di Forza
- **Disaccoppiamento Totale da `.env`**: I 20 test unitari (`pytest tests/`) vengono eseguiti con successo al 100% anche senza il file `.env` locale presente. Tutti i test usano mock espliciti (`unittest.mock`, `monkeypatch`) per isolare il codice dal sistema host.

#### ⚠️ Aree di Miglioramento
1. **Copertura degli Error Paths (Casi Limite)**:
   * Attualmente i test coprono brillantemente gli *happy path*, la validazione configurazione e i mock di successo.
   * Mancano test per i seguenti percorsi di fallimento:
     * Chiamata Notion che ritorna errore HTTP (es. status `400`, `403` o `500`).
     * Errore di timeout di rete durante la chiamata a Notion.
     * Fallimento di tutti i modelli Gemini in `analyzer.py` con sollevamento di `RuntimeError`.
     * URL non supportato o errore yt-dlp con eccezione sollevata.
2. **Pipeline CI su GitLab (`.gitlab-ci.yml`)**:
   * Il repository su `gitlab.example.com` non ha attualmente un file `.gitlab-ci.yml` per eseguire automaticamente i test e il linting ad ogni push.

---

## 📋 Piano di Azione Raccomandato (Task Prioritari)

Per portare il progetto a un punteggio di conformità del **100%** rispetto agli standard di Notion, si consigliano i seguenti interventi mirati:

### Task 1: Docker Healthcheck & Hardening (.dockerignore)
- Aggiungere la direttiva `HEALTHCHECK` in `Dockerfile`.
- Aggiungere `*.pem`, `*.key`, `*.db`, `tests/` in `.dockerignore`.

### Task 2: Robustezza Client Gemini (Timeout Esplicito)
- Impostare `http_options={"timeout": 60.0}` su `genai.Client` in `analyzer.py`.

### Task 3: Sanitizzazione Errori Utente in Telegram
- In `bot.py`, sostituire l'inclusione grezza di `safe_err_text = html.escape(str(e)[:300])` con messaggi chiari categorizzati per tipologia d'errore (Download, AI, Notion), confinando i dettagli diagnostici ai soli log interni del server.

### Task 4: Copertura Test Error Paths & GitLab CI
- Aggiungere test negativi in `tests/test_notion_sync.py` (simulazione errore HTTP 400/500 e timeout).
- Aggiungere test negativi in `tests/test_analyzer.py` (simulazione fallimento modelli).
- Creare `.gitlab-ci.yml` per lanciare `pytest` automaticamente ad ogni commit su GitLab.

---

*Report generato con successo da Antigravity Pair Programmer per l'homelab di Gas (`example.com`).*
