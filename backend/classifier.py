import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
)
_language = os.getenv("GPT_LANGUAGE", "en")

BATCH_SIZE = 50


def _classify_batch(
    tracks: list[dict],
    existing_categories: list[str] | None = None,
) -> dict[str, list[dict]]:
    track_info = "\n".join(
        f"- [{t['database_id']}] {t['name']} — {t['artist']} ({t['album']})"
        for t in tracks
    )

    category_hint = ""
    if existing_categories:
        category_hint = (
            f"\nUse these existing category names when possible: {', '.join(existing_categories)}. "
            "You may add new categories if needed."
        )

    prompt = f"""Classify the following music tracks into genre categories.
Decide the appropriate granularity yourself (e.g., "Indie Rock", "Synthwave", "Lo-fi Hip Hop").
Output all category names in {_language}.{category_hint}

Tracks:
{track_info}

Return ONLY valid JSON in this format:
{{"categories": {{"CategoryName": [{{"name": "...", "artist": "...", "database_id": 12345}}, ...]}}}}
"""

    for attempt in range(3):
        try:
            response = _client.responses.create(
                model="gpt-4.1-mini",
                input=prompt,
            )
            text = response.output_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(text)
            return data.get("categories", {})
        except (json.JSONDecodeError, KeyError, AttributeError):
            if attempt == 2:
                return {}
    return {}


def classify_tracks(
    tracks: list[dict],
    progress_callback=None,
) -> dict[str, list[dict]]:
    if len(tracks) <= BATCH_SIZE:
        if progress_callback:
            progress_callback("1/1 batches")
        return _classify_batch(tracks)

    batches = [tracks[i:i + BATCH_SIZE] for i in range(0, len(tracks), BATCH_SIZE)]
    total = len(batches)
    all_categories: dict[str, list[dict]] = {}
    existing_names: list[str] = []

    for idx, batch in enumerate(batches):
        if progress_callback:
            progress_callback(f"{idx + 1}/{total} batches")
        result = _classify_batch(batch, existing_names if existing_names else None)
        for cat_name, cat_tracks in result.items():
            if cat_name not in all_categories:
                all_categories[cat_name] = []
                existing_names.append(cat_name)
            all_categories[cat_name].extend(cat_tracks)

    # Validate: collect classified IDs
    classified_ids = set()
    valid_ids = {t["database_id"] for t in tracks}
    for cat_tracks in all_categories.values():
        cat_tracks[:] = [t for t in cat_tracks if t.get("database_id") in valid_ids]
        classified_ids.update(t["database_id"] for t in cat_tracks)

    # Uncategorized fallback
    uncategorized = [t for t in tracks if t["database_id"] not in classified_ids]
    if uncategorized:
        label = {"zh-CN": "未分类", "ja": "未分類"}.get(_language, "Uncategorized")
        all_categories[label] = uncategorized

    return all_categories


def pick_by_description(description: str, tracks: list[dict]) -> list[dict]:
    track_info = "\n".join(
        f"- [{t['database_id']}] {t['name']} — {t['artist']} ({t['album']})"
        for t in tracks
    )
    prompt = f"""From the following music tracks, select the ones that match this description: "{description}"

Tracks:
{track_info}

Return ONLY valid JSON: {{"track_ids": [12345, 67890, ...]}}
If no tracks match, return {{"track_ids": []}}
"""
    try:
        response = _client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
        )
        text = response.output_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(text)
        valid_ids = {t["database_id"] for t in tracks}
        matched_ids = set(data.get("track_ids", [])) & valid_ids
        return [t for t in tracks if t["database_id"] in matched_ids]
    except (json.JSONDecodeError, KeyError, AttributeError):
        return []
