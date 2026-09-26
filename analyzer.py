import os
import glob
import json
import base64
import logging
import subprocess
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

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
    tablature: str = Field(default="", description="Tablatura ASCII standard a 6 righe (e, B, G, D, A, E) formattata a larghezza fissa o stringa vuota se non applicabile")
    right_hand_technique: str = Field(default="", description="Spiegazione del pattern mano destra (es. arpeggio pollice-indice-medio, plettrata, ecc.) o indicazioni tecniche")
    execution_tips: List[str] = Field(default_factory=list, description="Consigli pratici ed ergonomici per suonare il passaggio o applicare i concetti")
    summary: str = Field(default="", description="Spiegazione del concetto armonico, trucco o consiglio didattico mostrato nel post")

def extract_audio_track(video_path: str, output_path: str) -> Optional[str]:
    """
    Estrae la traccia audio dal video convertendola in MP3 mono 16kHz compatto (64 kbps)
    per consentire a Gemini l'ascolto simultaneo di tonalità, tempo, arpeggi e strumming pattern.
    """
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-ar", "16000", "-ac", "1", "-b:a", "64k",
        output_path
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info("Traccia audio estratta con successo (%d bytes): %s", os.path.getsize(output_path), output_path)
            return output_path
        logger.warning("Estrazione audio ffmpeg terminata con codice %d o file vuoto", res.returncode)
        return None
    except Exception as e:
        logger.warning("Errore durante estrazione audio ffmpeg: %s", e)
        return None

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

def analyze_guitar_video(
    video_path: str,
    api_key: str,
    video_title: str = "",
    uploader: str = "",
    image_paths: Optional[List[str]] = None
) -> GuitarLesson:
    """
    Analizza i fotogrammi estratti dal video o le immagini di un post fotografico,
    integrando la traccia audio del video se disponibile (Analisi Bimodale Gemini),
    per ricavare tablatura, accordi, diteggiature, progressioni, tempo e consigli didattici.
    """
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=60000))

    has_audio = False
    if image_paths and len(image_paths) > 0:
        frames = image_paths
        logger.info("Utilizzo %d immagini fornite direttamente per l'analisi visiva", len(frames))
    else:
        tmp_dir = os.path.join(os.path.dirname(video_path), "frames")
        frames = extract_keyframes(video_path, tmp_dir, num_frames=8)

        # ARCH-2: Estrazione traccia audio per analisi bimodale (16kHz mono MP3 compresso)
        audio_output_path = os.path.join(os.path.dirname(video_path), "audio.mp3")
        extracted_audio = extract_audio_track(video_path, audio_output_path)
        if extracted_audio:
            has_audio = True

    if not frames:
        raise ValueError("Nessun fotogramma o immagine disponibile per l'analisi.")

    inputs = []
    # Inserimento fotogrammi visivi
    for fpath in frames:
        with open(fpath, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")
            inputs.append({"type": "image", "data": b64_data, "mime_type": "image/jpeg"})

    # Inserimento traccia audio se disponibile (Bimodal Analysis)
    if has_audio:
        try:
            with open(audio_output_path, "rb") as af:
                audio_b64 = base64.b64encode(af.read()).decode("utf-8")
                inputs.append({"type": "audio", "data": audio_b64, "mime_type": "audio/mp3"})
            logger.info("Traccia audio incorporata con successo negli input per Gemini")
        except Exception as err:
            logger.warning("Impossibile leggere il file audio per l'invio a Gemini: %s", err)

    audio_guidance = ""
    if has_audio:
        audio_guidance = (
            "- Ti è fornita anche la TRACCIA AUDIO ORIGINALE del video in MP3 mono.\n"
            "- Esegui un'ANALISI BIMODALE COMPLETA: ascolta la traccia audio per identificare a orecchio la reale tonalità (Key), "
            "i cambi di accordo esatti, il tempo, e il pattern della mano destra (strumming es. D-DU-UDU, arpeggio dita o plettrata).\n"
            "- Correla l'audio con le diteggiature e i movimenti delle mani osservati nei fotogrammi visivi per confermare ogni singola nota e voicing.\n"
        )

    prompt = f"""Sei un maestro di musica, chitarra ed esperto didattico/trascrittore professionista.
Ti sono forniti dei fotogrammi sequenziali o un'immagine/infografica didattica musicale (TikTok/Reel/Post).
Informazioni disponibili:
- Autore: {uploader or 'Creator'}
- Titolo post/video: {video_title or 'Lezione/Post Musicale'}
{audio_guidance}
Il tuo compito è analizzare con massima accuratezza sia ciò che è mostrato a schermo (diteggiature, accordi, nomi, box di accordi, tablature sovraimpresse, posizioni delle mani o schemi didattici) sia l'audio (se fornito).

DEVI restituire ESCLUSIVAMENTE un oggetto JSON valido conforme a questa struttura:
{{
  "title": "Titolo descrittivo del riff, brano o infografica (es. 'The Calling - Wherever You Will Go (Accordi Facili)' o 'Magic Chord Sequence')",
  "tuning": "Standard (E A D G B E) oppure accordatura specifica",
  "capo": "Nessuno oppure Capotasto al tasto X",
  "key": "Tonalità principale stimata",
  "progression": "Sequenza o progressione di accordi principale (es. C -> G -> Am -> F)",
  "chords": [
    {{
      "name": "Nome accordo (es. C, G, Am, F o voicings estesi)",
      "fingering": "Diteggiatura a 6 corde 'E A D G B e' (es. x 3 2 0 1 0)",
      "description": "Dettaglio posizione o dita usate"
    }}
  ],
  "tablature": "Se presente o applicabile, tablatura ASCII standard a 6 righe completa e pulita, allineata a spaziatura fissa:\\ne|---------...\\nB|---------...\\nG|---------...\\nD|---------...\\nA|---------...\\nE|---------...\\nAltrimenti lascia stringa vuota \\"\\"",
  "right_hand_technique": "Descrizione accurata del pattern mano destra (arpeggio, plettrata alternata, strumming pattern es. D-DU-UDU) oppure indicazioni tecniche",
  "execution_tips": [
    "Consiglio pratico 1",
    "Consiglio pratico 2"
  ],
  "summary": "Spiegazione didattica del concetto, trucco o progressione spiegata e come applicarla"
}}

Regole tassative:
- Se l'immagine è un'infografica con diverse progressioni o consigli (es. accordi per atmosfera/emozione, o consigli di produzione/EQ), estrai tutti gli accordi o i punti chiave con la massima cura.
- Se le tablature sono presenti, assicurati che siano rigorosamente allineate per tutte e 6 le corde.
- Non aggiungere markdown backtick (es. ```json) prima o dopo il JSON, restituisci solo il testo JSON puro.
"""
    inputs.append({"type": "text", "text": prompt})

    candidate_models = [
        "gemini-flash-latest",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.5-flash",
    ]

    lesson_schema = GuitarLesson.model_json_schema()
    response_format = {
        "type": "text",
        "mime_type": "application/json",
        "schema": lesson_schema,
    }

    last_error = None
    for model_name in candidate_models:
        try:
            logger.info("Chiamata modello Gemini: %s", model_name)
            try:
                # Tentativo primario: Structured Outputs nativo con schema Pydantic
                interaction = client.interactions.create(
                    model=model_name,
                    input=inputs,
                    response_format=response_format
                )
            except Exception as format_err:
                logger.warning("Structured outputs non supportato da %s (%s), fallback a prompt testuale", model_name, format_err)
                interaction = client.interactions.create(
                    model=model_name,
                    input=inputs
                )

            raw_text = interaction.output_text or ""
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

