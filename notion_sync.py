import json
import logging
import requests
from typing import Dict, Any
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

def publish_to_notion(lesson: GuitarLesson, original_url: str, uploader: str) -> str:
    """
    Crea una sottopagina formattata su Notion sotto la pagina radice CozyTabs.
    Restituisce l'URL della pagina Notion creata.
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

    # Creazione pagina Notion
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

    resp = requests.post(f"{NOTION_API_URL}/pages", headers=headers, json=body, timeout=20)
    if resp.status_code != 200:
        logger.error("Errore creazione pagina Notion: %s - %s", resp.status_code, resp.text)
        raise RuntimeError(f"Errore Notion API ({resp.status_code}): {resp.text}")

    page_data = resp.json()
    page_url = page_data.get("url", "")
    logger.info("Creata pagina Notion: %s (ID: %s)", page_url, page_data.get("id"))
    return page_url
