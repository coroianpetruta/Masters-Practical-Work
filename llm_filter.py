"""Natural-language filter interpretation and entity resolution."""

from __future__ import annotations

import difflib
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"


def _extract_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Model did not return JSON. Output:\n{text}")
    return json.loads(match.group(0))


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _tokens(text: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", _normalized(text)) if token}


@dataclass
class ResolutionCandidate:
    label: str
    score: float
    reason: str


def resolve_node_mention(
    mention: str,
    node_labels: Iterable[str],
    *,
    max_candidates: int = 5,
    min_score: float = 0.45,
) -> List[ResolutionCandidate]:
    """Return plausible label candidates for a free-text node mention."""
    mention_norm = _normalized(mention)
    mention_tokens = _tokens(mention)
    if not mention_norm:
        return []

    scored: List[ResolutionCandidate] = []
    for label in node_labels:
        label_norm = _normalized(label)
        label_tokens = _tokens(label)
        if not label_norm:
            continue

        reason = "fuzzy match"
        score = difflib.SequenceMatcher(None, mention_norm, label_norm).ratio()
        if mention_norm == label_norm:
            score = 1.0
            reason = "exact match"
        elif mention_norm in label_norm:
            score = max(score, 0.92)
            reason = "label contains mention"
        elif mention_tokens and mention_tokens.issubset(label_tokens):
            score = max(score, 0.88)
            reason = "token match"
        elif mention_tokens and mention_tokens & label_tokens:
            overlap = len(mention_tokens & label_tokens) / len(mention_tokens)
            score = max(score, 0.62 + overlap * 0.2)
            reason = "partial token match"

        if score >= min_score:
            scored.append(ResolutionCandidate(label=str(label), score=score, reason=reason))

    scored.sort(key=lambda item: (-item.score, item.label.lower()))
    return scored[:max_candidates]


def normalize_llm_filter(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize model output into the deterministic filter spec shape."""
    relationship_mode = str(raw.get("relationship_mode") or "union").strip().lower()
    if relationship_mode not in {"union", "intersection", "path", "selected_only"}:
        relationship_mode = "union"

    try:
        hop_depth = int(raw.get("hop_depth", 1))
    except Exception:
        hop_depth = 1

    return {
        "seed_node_mentions": [str(x).strip() for x in raw.get("seed_node_mentions", []) if str(x).strip()],
        "selected_kinds": [str(x).strip().lower() for x in raw.get("selected_kinds", []) if str(x).strip()],
        "selected_edge_labels": [str(x).strip() for x in raw.get("selected_edge_labels", []) if str(x).strip()],
        "relationship_mode": relationship_mode,
        "hop_depth": max(0, min(5, hop_depth)),
        "include_seed_nodes": bool(raw.get("include_seed_nodes", True)),
        "time_start_label": raw.get("time_start_label"),
        "time_end_label": raw.get("time_end_label"),
        "explanation": str(raw.get("explanation", "")).strip(),
    }


def _resolve_allowed_options(values: Iterable[Any], allowed: Iterable[str]) -> List[str]:
    allowed_list = list(allowed)
    by_norm = {
        re.sub(r"[^a-z0-9]+", "", _normalized(option)): option
        for option in allowed_list
    }
    resolved: List[str] = []
    for value in values:
        norm = re.sub(r"[^a-z0-9]+", "", _normalized(value))
        if norm in by_norm and by_norm[norm] not in resolved:
            resolved.append(by_norm[norm])
    return resolved


def interpret_filter_query(
    query: str,
    *,
    node_kinds: List[str],
    edge_labels: List[str],
    time_labels: List[str],
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout_s: int = 60,
) -> Dict[str, Any]:
    """Ask DeepSeek to translate natural language into a filter intent."""
    api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY.")

    model = model or os.getenv("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL)
    base_url = (base_url or os.getenv("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL)).rstrip("/")
    url = f"{base_url}/chat/completions"

    schema = {
        "seed_node_mentions": ["free-text node/person/team/etc mentions from the query"],
        "selected_kinds": node_kinds,
        "selected_edge_labels": edge_labels,
        "relationship_mode": "union | intersection | path | selected_only",
        "hop_depth": "integer 0-5",
        "include_seed_nodes": True,
        "time_start_label": "one of the available timestep labels or null",
        "time_end_label": "one of the available timestep labels or null",
        "explanation": "short interpretation",
    }
    system = (
        "You translate a user graph-filter request into JSON only. "
        "Do not invent exact node labels. Put people/entities mentioned by the user in "
        "seed_node_mentions as written or lightly normalized. Use selected_kinds and "
        "selected_edge_labels only from the allowed options. "
        "Use relationship_mode='intersection' when the user asks for things shared by all "
        "selected entities, 'union' for any/each, 'path' for connections between selected "
        "entities, and 'selected_only' only when they ask to show just those entities. "
        "If a time range is mentioned, map it to available timestep labels when possible, "
        "but the UI timeline remains the source of truth for time display."
    )
    user = {
        "query": query,
        "allowed_node_kinds": node_kinds,
        "allowed_edge_labels": edge_labels,
        "available_time_labels": time_labels,
        "json_schema": schema,
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        "temperature": 0,
        "max_tokens": 1200,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DeepSeek HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"DeepSeek connection error: {exc}") from exc

    content = payload["choices"][0]["message"]["content"]
    interpreted = normalize_llm_filter(_extract_json(content))
    interpreted["selected_kinds"] = _resolve_allowed_options(interpreted["selected_kinds"], node_kinds)
    interpreted["selected_edge_labels"] = _resolve_allowed_options(
        interpreted["selected_edge_labels"],
        edge_labels,
    )
    interpreted["time_start_label"] = next(
        (label for label in time_labels if str(label) == str(interpreted.get("time_start_label"))),
        interpreted.get("time_start_label"),
    )
    interpreted["time_end_label"] = next(
        (label for label in time_labels if str(label) == str(interpreted.get("time_end_label"))),
        interpreted.get("time_end_label"),
    )
    return interpreted
