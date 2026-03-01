"""Neo4j and source document data access."""

import json
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from neo4j import GraphDatabase

from time_utils import parse_dt

@dataclass
class EdgeRow:
    edge_id: str
    source_id: str
    target_id: str
    source_label: str
    target_label: str
    rel_name: str
    valid_at: Optional[datetime]
    invalid_at: Optional[datetime]
    created_at: Optional[datetime]
    episode_uuids: List[str]


@dataclass
class EpisodeRow:
    uuid: str
    source_text_name: Optional[str]
    context: str
    created_at: Optional[datetime]


def fetch_edges(
    uri: str,
    user: str,
    password: str,
    database: Optional[str],
    rel_name: str = "PLAYER_PLAYS_FOR_TEAM",
    limit: int = 5000,
) -> List[EdgeRow]:
    """
    Tries to be resilient across Graphiti-ish schemas:
    - Relationship property may be `name` or relationship type might be generic with `name` property.
    - We match by relationship property `name = rel_name` if present; otherwise by relationship type.
    """

    driver = GraphDatabase.driver(uri, auth=(user, password))
    query = """
        MATCH (s)-[r]->(t)
    WHERE
        (
            r.name IS NOT NULL AND
            toLower(r.name) = "player_plays_for_team"
        )
        OR
        toLower(type(r)) = "player_plays_for_team"
    RETURN
        coalesce(r.uuid, r.id, toString(id(r))) AS edge_id,
        coalesce(s.uuid, s.id, toString(id(s))) AS source_id,
        coalesce(t.uuid, t.id, toString(id(t))) AS target_id,
        coalesce(s.name, s.title, s.label, head(labels(s)), 'Node') AS source_label,
        coalesce(t.name, t.title, t.label, head(labels(t)), 'Node') AS target_label,
        coalesce(r.name, type(r)) AS rel_name,
        r.valid_at AS valid_at,
        r.invalid_at AS invalid_at,
        r.created_at AS created_at,
        coalesce(r.episodes, []) AS episodes
    LIMIT $limit
    """

    rows: List[EdgeRow] = []
    with driver.session(database=database) as session:
        for rec in session.run(query, rel_name=rel_name, limit=limit):
            rows.append(
                EdgeRow(
                    edge_id=str(rec["edge_id"]),
                    source_id=str(rec["source_id"]),
                    target_id=str(rec["target_id"]),
                    source_label=str(rec["source_label"]),
                    target_label=str(rec["target_label"]),
                    rel_name=str(rec["rel_name"]),
                    valid_at=parse_dt(rec["valid_at"]),
                    invalid_at=parse_dt(rec["invalid_at"]),
                    created_at=parse_dt(rec["created_at"]),
                    episode_uuids=[str(x) for x in (rec["episodes"] or []) if x is not None],
                )
            )
    driver.close()
    return rows


def load_source_documents() -> Dict[str, Dict[str, str]]:
    base_dir = Path(__file__).resolve().parent
    sources_path = base_dir / "data" / "sources.json"
    if not sources_path.exists():
        return {}

    with sources_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    docs: Dict[str, Dict[str, str]] = {}
    for entry in raw.get("entries", []):
        name = str(entry.get("file_name", "")).strip()
        if not name:
            continue
        txt_path = sources_path.parent / f"{name}.txt"
        try:
            text = txt_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            text = ""
        docs[name] = {
            "date_accessed": str(entry.get("date_accessed", "")).strip(),
            "link": str(entry.get("link", "")).strip(),
            "text": text,
        }
    return docs


def fetch_episodes_and_mentions(
    uri: str,
    user: str,
    password: str,
    database: Optional[str],
) -> Tuple[Dict[str, EpisodeRow], Dict[str, Set[str]]]:
    """
    Returns:
      - episode_map: ep_uuid -> episode metadata
      - node_to_episode_uuids: node_id -> {ep_uuid, ...}
    """
    driver = GraphDatabase.driver(uri, auth=(user, password))
    episode_q = """
    MATCH (ep:Episodic)
    RETURN
      ep.uuid AS ep_uuid,
      ep.source_text_name AS source_text_name,
      coalesce(ep.context, ep.content, ep.text, '') AS context,
      ep.created_at AS created_at
    """
    mentions_q = """
    MATCH (ep:Episodic)-[:MENTIONS]-(n)
    WHERE ep.uuid IS NOT NULL
    RETURN
      coalesce(n.uuid, n.id, toString(id(n))) AS node_id,
      collect(DISTINCT ep.uuid) AS episode_uuids
    """

    episode_map: Dict[str, EpisodeRow] = {}
    node_to_eps: Dict[str, Set[str]] = {}
    with driver.session(database=database) as session:
        for rec in session.run(episode_q):
            ep_uuid = rec["ep_uuid"]
            if not ep_uuid:
                continue
            episode_map[str(ep_uuid)] = EpisodeRow(
                uuid=str(ep_uuid),
                source_text_name=(str(rec["source_text_name"]) if rec["source_text_name"] is not None else None),
                context=str(rec["context"] or ""),
                created_at=parse_dt(rec["created_at"]),
            )
        for rec in session.run(mentions_q):
            node_id = str(rec["node_id"])
            uuids = {str(x) for x in (rec["episode_uuids"] or []) if x}
            node_to_eps[node_id] = uuids
    driver.close()
    return episode_map, node_to_eps
