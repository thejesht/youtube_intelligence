"""
Wiki Update — Build a compounding knowledge base from video transcripts.

Reads transcripts directly from Supabase, uses Ollama to extract
concepts and people, then creates/updates wiki markdown pages.

Usage:
  python -m pipeline.wiki_update
"""

import json
import re
import requests
from datetime import datetime
from pathlib import Path

from pipeline import storage
from pipeline.config import SUPABASE_URL

WIKI_DIR = Path(__file__).parent.parent / "wiki"
CONCEPTS_DIR = WIKI_DIR / "concepts"
PEOPLE_DIR = WIKI_DIR / "people"
SOURCES_DIR = WIKI_DIR / "sources"
THEMES_DIR = WIKI_DIR / "themes"

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "deepseek-v3.1:671b-cloud"

for d in [CONCEPTS_DIR, PEOPLE_DIR, SOURCES_DIR, THEMES_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug[:80]


def _ollama(prompt: str, max_tokens: int = 3000) -> str | None:
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                  "options": {"num_predict": max_tokens, "temperature": 0.3}},
            timeout=300,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except requests.exceptions.ConnectionError:
        print("  ERROR: Ollama not running. Start it with: ollama serve")
    except Exception as e:
        print(f"  Ollama error: {e}")
    return None


def _extract_json_array(text: str) -> list:
    try:
        start, end = text.find("["), text.rfind("]")
        if start != -1 and end != -1:
            return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        pass
    return []


def extract_knowledge_from_transcript(title: str, channel: str, transcript: str) -> dict:
    """Use LLM to extract concepts, people, and overview from raw transcript."""
    # Truncate to fit context window
    text = transcript[:50_000]

    prompt = f"""You are a knowledge extraction assistant. Read this YouTube video transcript and extract structured knowledge.

Return ONLY valid JSON with these fields:
{{
  "overview": "2-3 sentence overview",
  "key_topics": ["topic1", "topic2"],
  "key_takeaways": ["actionable insight 1", "insight 2"],
  "concepts": [
    {{"term": "Concept Name", "definition": "one-line explanation"}}
  ],
  "people": [
    {{"name": "Person Name", "context": "who they are and their relevance"}}
  ]
}}

Focus on ideas, frameworks, and techniques that a senior engineer moving into product/AI work would find valuable.

VIDEO: {title}
CHANNEL: {channel}

TRANSCRIPT:
{text}"""

    result = _ollama(prompt, max_tokens=3000)
    if not result:
        return {}

    # Extract JSON
    try:
        start, end = result.find("{"), result.rfind("}")
        if start != -1 and end != -1:
            return json.loads(result[start:end + 1])
    except json.JSONDecodeError:
        pass
    return {}


def create_source_page(video: dict, knowledge: dict) -> Path:
    slug = _slugify(video["title"])
    path = SOURCES_DIR / f"{slug}.md"

    overview = knowledge.get("overview", "")
    topics = knowledge.get("key_topics", [])
    takeaways = knowledge.get("key_takeaways", [])
    concepts = knowledge.get("concepts", [])

    content = f"""---
title: "{video['title']}"
channel: "{video['channel_name']}"
published: {video['published_at'][:10]}
url: {video['video_url']}
processed: {datetime.now().strftime('%Y-%m-%d')}
---

# {video['title']}

**Channel:** {video['channel_name']} | **Published:** {video['published_at'][:10]} | [Watch]({video['video_url']})

## Overview

{overview}

## Key Topics

{chr(10).join(f'- [[{t}]]' for t in topics)}

## Key Takeaways

{chr(10).join(f'- {t}' for t in takeaways)}

## Concepts

{chr(10).join(f'- **[[{c["term"]}]]**: {c["definition"]}' for c in concepts if isinstance(c, dict) and c.get("term"))}
"""
    path.write_text(content, encoding="utf-8")
    return path


def update_concept_page(term: str, definition: str, source_title: str, source_slug: str):
    slug = _slugify(term)
    path = CONCEPTS_DIR / f"{slug}.md"
    source_link = f"[[{source_slug}|{source_title}]]"

    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if source_title not in existing:
            if "## Sources" in existing:
                existing = existing.replace("## Sources", f"## Sources\n- {source_link}")
            else:
                existing += f"\n## Sources\n\n- {source_link}\n"
            path.write_text(existing, encoding="utf-8")
            print(f"    Updated concept: {term}")
    else:
        content = f"""---
title: "{term}"
type: concept
created: {datetime.now().strftime('%Y-%m-%d')}
---

# {term}

{definition}

## Sources

- {source_link}
"""
        path.write_text(content, encoding="utf-8")
        print(f"    Created concept: {term}")


def update_people_page(name: str, source_title: str, source_slug: str, context: str = ""):
    slug = _slugify(name)
    path = PEOPLE_DIR / f"{slug}.md"
    source_link = f"[[{source_slug}|{source_title}]]"

    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if source_title not in existing:
            if "## Appearances" in existing:
                existing = existing.replace("## Appearances", f"## Appearances\n- {source_link}")
            else:
                existing += f"\n## Appearances\n\n- {source_link}\n"
            path.write_text(existing, encoding="utf-8")
    else:
        content = f"""---
title: "{name}"
type: person
created: {datetime.now().strftime('%Y-%m-%d')}
---

# {name}

{context}

## Appearances

- {source_link}
"""
        path.write_text(content, encoding="utf-8")
        print(f"    Created person: {name}")


def update_index():
    concepts = sorted(CONCEPTS_DIR.glob("*.md"))
    people = sorted(PEOPLE_DIR.glob("*.md"))
    sources = sorted(SOURCES_DIR.glob("*.md"))
    themes = sorted(THEMES_DIR.glob("*.md"))

    def _link(path: Path, dir_name: str) -> str:
        text = path.read_text(encoding="utf-8")
        m = re.search(r'^title:\s*"?(.+?)"?\s*$', text, re.MULTILINE)
        title = m.group(1) if m else path.stem.replace("-", " ").title()
        return f"- [{title}]({dir_name}/{path.name})"

    content = f"""# YouTube Intelligence Wiki

> A compounding knowledge base built from YouTube video transcripts.
> Maintained by LLM. Curated by human.

## Concepts

{chr(10).join(_link(p, 'concepts') for p in concepts) or '*(none yet)*'}

## People

{chr(10).join(_link(p, 'people') for p in people) or '*(none yet)*'}

## Sources

{chr(10).join(_link(p, 'sources') for p in sources) or '*(none yet)*'}

## Themes

{chr(10).join(_link(p, 'themes') for p in themes) or '*(none yet)*'}

---

**Stats:** {len(sources)} sources | {len(concepts)} concepts | {len(people)} people | {len(themes)} themes
**Last updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
    (WIKI_DIR / "index.md").write_text(content, encoding="utf-8")


def append_log(operation: str, details: str):
    log_path = WIKI_DIR / "log.md"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n## [{datetime.now().strftime('%Y-%m-%d')}] {operation} | {details}\n")


def main():
    print(f"{'='*60}")
    print(f"Wiki Update - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    videos = storage.get_videos_pending_wiki()
    print(f"\n[WIKI] {len(videos)} videos with transcripts to process...\n")

    if not videos:
        print("Nothing to process. Wiki is up to date.")
        return

    for video in videos:
        title = video["title"]
        slug = _slugify(title)
        channel_name = storage.get_channel_name(video["channel_id"])
        video["channel_name"] = channel_name

        # Get transcript
        transcript = storage.get_transcript_text(video["video_id"])
        if not transcript or len(transcript.strip()) < 100:
            print(f"  Skipping {title[:50]} (transcript too short)")
            storage.mark_wiki_processed(video["video_id"])
            continue

        print(f"Processing: {title[:60]}...")

        # Extract knowledge from raw transcript
        print(f"  Extracting knowledge ({len(transcript.split())} words)...")
        knowledge = extract_knowledge_from_transcript(title, channel_name, transcript)

        if not knowledge:
            print(f"  FAILED — could not extract knowledge")
            continue

        # Create source page
        create_source_page(video, knowledge)
        print(f"  Created source page")

        # Create/update concept pages
        for c in knowledge.get("concepts", []):
            if isinstance(c, dict) and c.get("term"):
                update_concept_page(c["term"], c.get("definition", ""), title, slug)

        # Create/update people pages
        for p in knowledge.get("people", []):
            if isinstance(p, dict) and p.get("name"):
                update_people_page(p["name"], title, slug, p.get("context", ""))

        # Mark processed and log
        storage.mark_wiki_processed(video["video_id"])
        append_log("ingest", f"{title} ({channel_name})")
        print(f"  Done.\n")

    update_index()
    print(f"[WIKI] Index updated. Wiki update complete.")


if __name__ == "__main__":
    main()
