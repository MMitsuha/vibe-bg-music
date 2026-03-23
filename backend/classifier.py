import json
import os

from openai import OpenAI

from models import Track

_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
)
_language = os.getenv("GPT_LANGUAGE", "en")
_category_count = os.getenv("GPT_CATEGORY_COUNT", "")
_category_direction = os.getenv("GPT_CATEGORY_DIRECTION", "")

BATCH_SIZE = 50

_TRACK_FORMAT_HINT = """Each track is formatted as:
- [database_id] title — artist (album) [metadata]

Metadata fields (when available):
- genre: the genre tag from the music file
- year: release year
- bpm: beats per minute (tempo)
- composer: the songwriter/composer
- album_artist: the album-level artist (shown only if different from track artist)
- plays: how many times the user has played this track (indicates preference)"""


def _fmt_track(t: Track) -> str:
    parts = [f"[{t.database_id}] {t.name} — {t.artist} ({t.album})"]
    extras = []
    if t.genre:
        extras.append(f"genre:{t.genre}")
    if t.year:
        extras.append(f"year:{t.year}")
    if t.bpm:
        extras.append(f"bpm:{t.bpm}")
    if t.composer:
        extras.append(f"composer:{t.composer}")
    if t.album_artist and t.album_artist != t.artist:
        extras.append(f"album_artist:{t.album_artist}")
    if t.played_count:
        extras.append(f"plays:{t.played_count}")
    if extras:
        parts.append(f"[{', '.join(extras)}]")
    return "- " + " ".join(parts)


def _classify_batch(
    tracks: list[Track],
    existing_categories: list[str] | None = None,
) -> dict[str, list[int]]:
    track_info = "\n".join(_fmt_track(t) for t in tracks)

    category_hint = ""
    if existing_categories:
        category_hint = (
            f"\nUse these existing category names when possible: {', '.join(existing_categories)}. "
            "You may add new categories if needed."
        )

    count_hint = f"\nAim for approximately {_category_count} categories." if _category_count else ""
    direction_hint = f"\nClassification direction: {_category_direction}" if _category_direction else ""

    prompt = f"""Classify the following music tracks into genre categories.
Decide the appropriate granularity yourself (e.g., "Indie Rock", "Synthwave", "Lo-fi Hip Hop").
Output all category names in {_language}.{category_hint}{count_hint}{direction_hint}

{_TRACK_FORMAT_HINT}

Tracks:
{track_info}

Return ONLY valid JSON in this format:
{{"categories": {{"CategoryName": [12345, 67890, ...]}}}}
Use database_id integers only in the arrays."""

    for attempt in range(3):
        try:
            response = _client.responses.create(
                model="gpt-5.4",
                input=prompt,
                service_tier="priority",
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
    tracks: list[Track],
    progress_callback=None,
) -> dict[str, list[Track]]:
    track_lookup = {t.database_id: t for t in tracks}

    def resolve(id_map: dict[str, list[int]]) -> dict[str, list[Track]]:
        result = {}
        for cat_name, ids in id_map.items():
            resolved = [track_lookup[tid] for tid in ids if tid in track_lookup]
            if resolved:
                result[cat_name] = resolved
        return result

    if len(tracks) <= BATCH_SIZE:
        if progress_callback:
            progress_callback("1/1 batches")
        return resolve(_classify_batch(tracks))

    batches = [tracks[i : i + BATCH_SIZE] for i in range(0, len(tracks), BATCH_SIZE)]
    total = len(batches)
    all_ids: dict[str, list[int]] = {}
    existing_names: list[str] = []

    for idx, batch in enumerate(batches):
        if progress_callback:
            progress_callback(f"{idx + 1}/{total} batches")
        result = _classify_batch(batch, existing_names if existing_names else None)
        for cat_name, ids in result.items():
            if cat_name not in all_ids:
                all_ids[cat_name] = []
                existing_names.append(cat_name)
            all_ids[cat_name].extend(ids)

    categories = resolve(all_ids)

    classified_ids = {t.database_id for cat_tracks in categories.values() for t in cat_tracks}
    uncategorized = [t for t in tracks if t.database_id not in classified_ids]
    if uncategorized:
        label = {"zh-CN": "未分类", "ja": "未分類"}.get(_language, "Uncategorized")
        categories[label] = uncategorized

    return categories


def pick_by_description(description: str, tracks: list[Track]) -> list[Track]:
    track_info = "\n".join(_fmt_track(t) for t in tracks)
    prompt = f"""From the following music tracks, select the ones that match this description: "{description}"

{_TRACK_FORMAT_HINT}

Tracks:
{track_info}

Return ONLY valid JSON: {{"track_ids": [12345, 67890, ...]}}
If no tracks match, return {{"track_ids": []}}
"""
    try:
        response = _client.responses.create(
            model="gpt-5.4",
            input=prompt,
            service_tier="priority",
        )
        text = response.output_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(text)
        valid_ids = {t.database_id for t in tracks}
        matched_ids = set(data.get("track_ids", [])) & valid_ids
        return [t for t in tracks if t.database_id in matched_ids]
    except (json.JSONDecodeError, KeyError, AttributeError):
        return []
