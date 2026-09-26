import json
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional
from analyzer import GuitarLesson
from config import Config

logger = logging.getLogger(__name__)

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

def split_text_chunks(text: str, max_length: int = 1900) -> list[str]:
    """Divide un testo lungo in chunk non superiori a max_length caratteri preservando le righe."""
    if not text:
        return []
    if len(text) <= max_length:
        return [text]

    lines = text.split("\n")
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_len = 0

    for line in lines:
        if current_len + len(line) + 1 > max_length:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_len = 0
            while len(line) > max_length:
                chunks.append(line[:max_length])
                line = line[max_length:]
        current_chunk.append(line)
        current_len += len(line) + 1

    if current_chunk:
        chunks.append("\n".join(current_chunk))
    return chunks

def publish_to_notion(
    lesson: GuitarLesson,
    original_url: str,
    uploader: str,
    cover_url: Optional[str] = None,
    media_type: str = "video"
) -> str:
    """
    Crea una scheda formattata su Notion (all'interno del Database CozyTabs o come sottopagina).
    Valorizza proprietà strutturate (Tonalità, Accordi, Accordatura, Cover, ecc.) e restituisce l'URL.
    """
    headers = {
        "Authorization": f"Bearer {Config.NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }

    # Costruzione blocchi Notion
    children: list[Dict[str, Any]] = [
        # Callout metadati
        {
            "object": "block",
            "type": "callout",
            "callout": {
                "icon": {"type": "emoji", "emoji": "ℹ️"},
                "rich_text": [
                    {"type": "text", "text": {"content": f"👤 Autore: {uploader}\n"}},
                    {"type": "text", "text": {"content": f"🎵 Tonalità: {lesson.key or 'N/D'} | ⚙️ Accordatura: {lesson.tuning} | Capotasto: {lesson.capo}\n"}},
                    *([{"type": "text", "text": {"content": f"🎶 Progressione: {lesson.progression}\n"}}] if lesson.progression else []),
                    {"type": "text", "text": {"content": "🔗 Post/Video originale: "}},
                    {"type": "text", "text": {"content": original_url, "link": {"url": original_url}}}
                ]
            }
        }
    ]

    # Sezione Accordi
    if lesson.chords:
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Accordi & Diteggiature (E A D G B e)"}}]
            }
        })
        for chord in lesson.chords:
            chord_desc = f" — {chord.description[:500]}" if chord.description else ""
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {"type": "text", "text": {"content": chord.name[:100]}, "annotations": {"bold": True}},
                        {"type": "text", "text": {"content": " : "}},
                        {"type": "text", "text": {"content": chord.fingering[:50]}, "annotations": {"code": True}},
                        {"type": "text", "text": {"content": chord_desc}}
                    ]
                }
            })

    # Sezione Tablatura (con chunking per rispettare il limite Notion di 2000 caratteri)
    if lesson.tablature and lesson.tablature.strip():
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Tablatura Esecuzione"}}]
            }
        })
        for tab_chunk in split_text_chunks(lesson.tablature.strip(), 1900):
            children.append({
                "object": "block",
                "type": "code",
                "code": {
                    "caption": [],
                    "language": "plain text",
                    "rich_text": [{"type": "text", "text": {"content": tab_chunk}}]
                }
            })

    # Sezione Tecnica Mano Destra
    if lesson.right_hand_technique:
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Mano Destra & Arpeggio"}}]
            }
        })
        for chunk in split_text_chunks(lesson.right_hand_technique, 1900):
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}]
                }
            })

    # Consigli per lo Studio
    if lesson.execution_tips:
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Consigli di Esecuzione"}}]
            }
        })
        for tip in lesson.execution_tips:
            tip_text = tip[:1900]
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": tip_text}}]
                }
            })

    # Riassunto/Concetto
    if lesson.summary:
        summary_chunks = split_text_chunks(lesson.summary, 1800)
        children.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "icon": {"type": "emoji", "emoji": "💡"},
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": "Concetto Chiave: "},
                        "annotations": {"bold": True}
                    },
                    {
                        "type": "text",
                        "text": {"content": summary_chunks[0] if summary_chunks else ""}
                    }
                ]
            }
        })
        for extra_summary in summary_chunks[1:]:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": extra_summary}}]
                }
            })

    # Creazione pagina Notion (nel Database o come sottopagina)
    if Config.NOTION_DATABASE_ID:
        format_label = "Infografica Foto" if media_type == "photo" else "Video Lezione"
        db_properties: Dict[str, Any] = {
            "Titolo": {
                "title": [{"type": "text", "text": {"content": lesson.title[:200]}}]
            },
            "Autore": {
                "rich_text": [{"type": "text", "text": {"content": uploader[:200]}}]
            },
            "Formato": {
                "select": {"name": format_label}
            },
            "Link Originale": {
                "url": original_url
            },
            "Data": {
                "date": {"start": datetime.now().strftime("%Y-%m-%d")}
            }
        }
        if lesson.key:
            db_properties["Tonalità"] = {"select": {"name": lesson.key[:100].replace(",", "")}}
        if lesson.tuning:
            db_properties["Accordatura"] = {"select": {"name": lesson.tuning[:100].replace(",", "")}}
        if lesson.capo:
            db_properties["Capotasto"] = {"rich_text": [{"type": "text", "text": {"content": lesson.capo[:100]}}]}

        if lesson.chords:
            clean_chords = []
            seen = set()
            for c in lesson.chords[:12]:
                c_name = c.name.strip().replace(",", "")[:100]
                if c_name and c_name not in seen:
                    clean_chords.append({"name": c_name})
                    seen.add(c_name)
            if clean_chords:
                db_properties["Accordi"] = {"multi_select": clean_chords}

        body: Dict[str, Any] = {
            "parent": {"database_id": Config.NOTION_DATABASE_ID},
            "icon": {"type": "emoji", "emoji": "🎸"},
            "properties": db_properties,
            "children": children
        }
    else:
        body = {
            "parent": {"page_id": Config.NOTION_PARENT_PAGE_ID},
            "icon": {"type": "emoji", "emoji": "🎸"},
            "properties": {
                "title": {
                    "title": [{"type": "text", "text": {"content": lesson.title}}]
                }
            },
            "children": children
        }

    # Impostazione immagine di copertina della scheda (Cover)
    if cover_url and cover_url.startswith("http"):
        body["cover"] = {"type": "external", "external": {"url": cover_url}}

    resp = requests.post(f"{NOTION_API_URL}/pages", headers=headers, json=body, timeout=20)
    if resp.status_code != 200:
        logger.error("Errore creazione pagina Notion: %s - %s", resp.status_code, resp.text)
        raise RuntimeError(f"Errore Notion API ({resp.status_code}): {resp.text}")

    page_data = resp.json()
    page_url = page_data.get("url", "")
    logger.info("Creata scheda su Notion: %s (ID: %s)", page_url, page_data.get("id"))
    return page_url
