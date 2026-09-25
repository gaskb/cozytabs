import os
import glob
import json
import base64
import logging
import subprocess
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai

logger = logging.getLogger(__name__)

class Chord(BaseModel):
    name: str = Field(description="Nome dell'accordo, es. Aadd#4 o C#m9")
    fingering: str = Field(description="Diteggiatura nel formato standard a 6 corde 'e-B-G-D-A-E' o 'E A D G B e', es. x0x440")
    description: Optional[str] = Field(default="", description="Spiegazione tasti e corde")

class GuitarLesson(BaseModel):
    title: str = Field(description="Titolo sintetico ed evocativo del riff o della lezione")
    tuning: str = Field(default="Standard (E A D G B E)", description="Accordatura della chitarra")
    capo: str = Field(default="Nessuno", description="Posizione del capotasto, se presente")
    key: str = Field(default="", description="Tonalità stimata del brano o della progressione")
    progression: str = Field(default="", description="Progressione accordi, es. A -> B -> C#m -> G#m")
    chords: List[Chord] = Field(default_factory=list, description="Lista degli accordi con relative diteggiature")
    tablature: str = Field(description="Tablatura ASCII standard a 6 righe (e, B, G, D, A, E) formattata a larghezza fissa")
    right_hand_technique: str = Field(default="", description="Spiegazione del pattern mano destra (es. arpeggio pollice-indice-medio, plettrata, ecc.)")
    execution_tips: List[str] = Field(default_factory=list, description="Consigli pratici ed ergonomici per suonare il passaggio")
    summary: str = Field(description="Spiegazione del concetto armonico o del trucco mostrato nel video")

def extract_keyframes(video_path: str, output_dir: str, num_frames: int = 8) -> List[str]:
    """
    Estrae fotogrammi chiave equidistanti dal video per l'analisi visiva con Gemini.
    """
    os.makedirs(output_dir, exist_ok=True)
    # Pulizia frame precedenti
    for old_f in glob.glob(os.path.join(output_dir, "frame_*.jpg")):
        try:
            os.remove(old_f)
        except OSError:
            pass

    # Ottieni la durata del video con ffprobe
    probe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path
    ]
    try:
        dur_str = subprocess.check_output(probe_cmd).decode().strip()
        duration = float(dur_str)
    except Exception as e:
        logger.warning("Impossibile determinare la durata precisa con ffprobe: %s. Uso default 15s.", e)
        duration = 15.0

    interval = max(1.0, duration / (num_frames + 1))
    extracted = []

    for i in range(1, num_frames + 1):
        ts = i * interval
        out_file = os.path.join(output_dir, f"frame_{i:02d}.jpg")
        cmd = [
            "ffmpeg", "-y", "-ss", str(ts), "-i", video_path,
            "-vframes", "1", "-q:v", "2", out_file
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(out_file):
            extracted.append(out_file)

    logger.info("Estratti %d fotogrammi da %s", len(extracted), video_path)
    return extracted

def analyze_guitar_video(video_path: str, api_key: str, video_title: str = "", uploader: str = "") -> GuitarLesson:
    """
    Analizza i fotogrammi estratti dal video usando Gemini Flash per ricavare
    tablatura, accordi, diteggiature e consigli didattici.
    """
    client = genai.Client(api_key=api_key)
    tmp_dir = os.path.join(os.path.dirname(video_path), "frames")
    frames = extract_keyframes(video_path, tmp_dir, num_frames=8)

    if not frames:
        raise ValueError("Nessun fotogramma estratto dal video.")

    inputs = []
    for fpath in frames:
        with open(fpath, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")
            inputs.append({"type": "image", "data": b64_data, "mime_type": "image/jpeg"})

    prompt = f"""Sei un maestro di chitarra esperto e trascrittore musicale professionista.
Ti sono forniti dei fotogrammi sequenziali estratti da un video didattico/musicale di chitarra (TikTok/Reel).
Informazioni disponibili:
- Autore: {uploader or 'Creator'}
- Titolo video: {video_title or 'Video Chitarra'}

Il tuo compito è analizzare la grafica a schermo (nomi di accordi, diteggiature, box di accordi, tablature sovraimpresse) e le mani del chitarrista sul manico per ricavare la trascrizione più fedele, leggibile e utile per lo studio.

DEVI restituire ESCLUSIVAMENTE un oggetto JSON valido conforme a questa struttura:
{{
  "title": "Titolo descrittivo del riff o della progressione (es. Voicings Aperti Moderni per A - B - C#m - G#m)",
  "tuning": "Standard (E A D G B E) oppure accordatura specifica",
  "capo": "Nessuno oppure Capotasto al tasto X",
  "key": "Tonalità principale stimata",
  "progression": "Sequenza accordi principale (es. Aadd#4 -> B(add11) -> C#m9 -> G#m(b6))",
  "chords": [
    {{
      "name": "Nome accordo (es. Aadd#4)",
      "fingering": "Diteggiatura precisa a 6 corde 'E A D G B e' (es. x 0 x 4 4 0)",
      "description": "Dettaglio corde e dita usate"
    }}
  ],
  "tablature": "Tablatura ASCII standard a 6 righe completa e pulita, allineata a spaziatura fissa:\\ne|---------...\\nB|---------...\\nG|---------...\\nD|---------...\\nA|---------...\\nE|---------...",
  "right_hand_technique": "Descrizione accurata della mano destra (es. arpeggio con pollice sul basso e dita sulle corde acute, plettrata alternata, ecc.)",
  "execution_tips": [
    "Consiglio pratico di postura/diteggiatura 1",
    "Consiglio pratico 2"
  ],
  "summary": "Breve spiegazione del trucco/concetto musicale spiegato nel video e come applicarlo"
}}

Attenzione:
- Assicurati che le tablature siano allineate e corrette per tutte e 6 le corde.
- Se noti refusi nella grafica del creator a schermo rispetto a come suona la mano, segnalalo e usa la diteggiatura corretta.
- Non aggiungere markdown backtick (es. ```json) prima o dopo il JSON, restituisci solo il testo JSON puro.
"""
    inputs.append({"type": "text", "text": prompt})

    candidate_models = [
        "gemini-3.5-flash",
        "gemini-3.7-flash",
        "gemini-3.1-flash-lite",
        "gemini-3.8-flash",
    ]

    last_error = None
    for model_name in candidate_models:
        try:
            logger.info("Chiamata modello Gemini: %s", model_name)
            interaction = client.interactions.create(
                model=model_name,
                input=inputs
            )
            raw_text = interaction.output_text or ""
            # Pulizia eventuali delimitatori di blocco codice
            cleaned = raw_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            return GuitarLesson(**parsed)
        except Exception as e:
            logger.warning("Modello %s non disponibile o errore: %s", model_name, e)
            last_error = e

    raise RuntimeError(f"Tutti i modelli Gemini candidati hanno fallito. Ultimo errore: {last_error}")
