"""Neo4j and source document data access."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from neo4j import GraphDatabase

from time_utils import parse_dt


CUSTOM_NODE_LABELS = [
    "Player",
    "Team",
    "Coach",
    "Match",
    "Competition",
    "GoalEvent",
    "InjuryEvent",
    "TransferEvent",
    "RetirementEvent",
    "Award",
    "Record",
    "Stadium",
]

CUSTOM_REL_NAMES = [
    "player_plays_for_team",
    "coach_manages_team",
    "team_participates_in_competition",
    "team_participates_in_match",
    "player_participates_in_match",
    "player_part_of_goal_event",
    "goal_event_part_of_match",
    "goal_event_scored_for_team",
    "player_part_of_transfer_event",
    "transfer_event_to_team",
    "transfer_event_from_team",
    "injury_of_player",
    "retirement_of_player_or_coach",
    "award_to_recipient",
    "record_held_by_entity",
    "stadium_hosts_match",
    "stadium_home_of_team",
]


@dataclass
class NodeRow:
    node_id: str
    label: str
    created_at: Optional[datetime]
    labels: List[str] = field(default_factory=list)

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
    source_labels: List[str] = field(default_factory=list)
    target_labels: List[str] = field(default_factory=list)


@dataclass
class EpisodeRow:
    uuid: str
    source_text_name: Optional[str]
    context: str
    created_at: Optional[datetime]


def _serialize_dt(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def _serialize_edge_row(edge: EdgeRow) -> Dict[str, Any]:
    data = asdict(edge)
    data["valid_at"] = _serialize_dt(edge.valid_at)
    data["invalid_at"] = _serialize_dt(edge.invalid_at)
    data["created_at"] = _serialize_dt(edge.created_at)
    return data


def _serialize_episode_row(episode: EpisodeRow) -> Dict[str, Any]:
    data = asdict(episode)
    data["created_at"] = _serialize_dt(episode.created_at)
    return data


def _serialize_node_row(node: NodeRow) -> Dict[str, Any]:
    data = asdict(node)
    data["created_at"] = _serialize_dt(node.created_at)
    return data


def save_demo_dataset(
    path: Path,
    nodes: List[NodeRow],
    edges: List[EdgeRow],
    episode_map: Dict[str, EpisodeRow],
    node_to_episode_uuids: Dict[str, Set[str]],
    source_docs: Dict[str, Dict[str, str]],
) -> None:
    payload = {
        "nodes": [_serialize_node_row(node) for node in nodes],
        "edges": [_serialize_edge_row(edge) for edge in edges],
        "episodes": {uuid: _serialize_episode_row(ep) for uuid, ep in episode_map.items()},
        "node_to_episode_uuids": {
            node_id: sorted(uuids) for node_id, uuids in node_to_episode_uuids.items()
        },
        "source_docs": source_docs,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_demo_dataset(
    path: Path,
) -> Tuple[List[NodeRow], List[EdgeRow], Dict[str, EpisodeRow], Dict[str, Set[str]], Dict[str, Dict[str, str]]]:
    raw = json.loads(path.read_text(encoding="utf-8"))

    nodes = [
        NodeRow(
            node_id=str(item["node_id"]),
            label=str(item["label"]),
            created_at=parse_dt(item.get("created_at")),
            labels=[str(lbl) for lbl in item.get("labels", []) if lbl],
        )
        for item in raw.get("nodes", [])
    ]

    edges = [
        EdgeRow(
            edge_id=str(item["edge_id"]),
            source_id=str(item["source_id"]),
            target_id=str(item["target_id"]),
            source_label=str(item["source_label"]),
            target_label=str(item["target_label"]),
            rel_name=str(item["rel_name"]),
            valid_at=parse_dt(item.get("valid_at")),
            invalid_at=parse_dt(item.get("invalid_at")),
            created_at=parse_dt(item.get("created_at")),
            episode_uuids=[str(x) for x in item.get("episode_uuids", []) if x is not None],
            source_labels=[str(lbl) for lbl in item.get("source_labels", []) if lbl],
            target_labels=[str(lbl) for lbl in item.get("target_labels", []) if lbl],
        )
        for item in raw.get("edges", [])
    ]

    episode_map = {
        str(uuid): EpisodeRow(
            uuid=str(uuid),
            source_text_name=(str(item["source_text_name"]) if item.get("source_text_name") is not None else None),
            context=str(item.get("context", "")),
            created_at=parse_dt(item.get("created_at")),
        )
        for uuid, item in raw.get("episodes", {}).items()
    }

    node_to_episode_uuids = {
        str(node_id): {str(uuid) for uuid in uuids if uuid}
        for node_id, uuids in raw.get("node_to_episode_uuids", {}).items()
    }
    source_docs = {
        str(name): {
            "date_accessed": str(doc.get("date_accessed", "")),
            "link": str(doc.get("link", "")),
            "text": str(doc.get("text", "")),
        }
        for name, doc in raw.get("source_docs", {}).items()
    }
    return nodes, edges, episode_map, node_to_episode_uuids, source_docs


def fetch_nodes(
    uri: str,
    user: str,
    password: str,
    database: Optional[str],
    allowed_labels: Optional[List[str]] = None,
    limit: Optional[int] = 5000,
) -> List[NodeRow]:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    allowed_labels = allowed_labels or CUSTOM_NODE_LABELS
    query = """
        MATCH (n:Entity)
        WHERE any(lbl IN labels(n) WHERE lbl IN $allowed_labels)
        RETURN
            coalesce(n.uuid, n.id, toString(id(n))) AS node_id,
            coalesce(n.name, n.title, n.label, head(labels(n)), 'Node') AS label,
            n.created_at AS created_at,
            labels(n) AS labels
    """
    if limit is not None:
        query += "\n        LIMIT $limit"

    rows: List[NodeRow] = []
    with driver.session(database=database) as session:
        params: Dict[str, Any] = {"allowed_labels": allowed_labels}
        if limit is not None:
            params["limit"] = limit
        for rec in session.run(query, **params):
            rows.append(
                NodeRow(
                    node_id=str(rec["node_id"]),
                    label=str(rec["label"]),
                    created_at=parse_dt(rec["created_at"]),
                    labels=[str(x) for x in (rec["labels"] or []) if x],
                )
            )
    driver.close()
    return rows


def fetch_edges(
    uri: str,
    user: str,
    password: str,
    database: Optional[str],
    rel_names: Optional[List[str]] = None,
    limit: Optional[int] = 5000,
) -> List[EdgeRow]:
    """
    Tries to be resilient across Graphiti-ish schemas:
    - Relationship property may be `name` or relationship type might be generic with `name` property.
    - We match by relationship property `name = rel_name` if present; otherwise by relationship type.
    """

    driver = GraphDatabase.driver(uri, auth=(user, password))
    rel_names = rel_names or CUSTOM_REL_NAMES
    query = """
        MATCH (s)-[r]->(t)
        WHERE
            (
                r.name IS NOT NULL AND
                toLower(r.name) IN $rel_names
            )
            OR
            toLower(type(r)) IN $rel_names
    RETURN
        coalesce(r.uuid, r.id, toString(id(r))) AS edge_id,
        coalesce(s.uuid, s.id, toString(id(s))) AS source_id,
        coalesce(t.uuid, t.id, toString(id(t))) AS target_id,
        coalesce(s.name, s.title, s.label, head(labels(s)), 'Node') AS source_label,
        coalesce(t.name, t.title, t.label, head(labels(t)), 'Node') AS target_label,
        labels(s) AS source_labels,
        labels(t) AS target_labels,
        coalesce(r.name, type(r)) AS rel_name,
        r.valid_at AS valid_at,
        r.invalid_at AS invalid_at,
        r.created_at AS created_at,
        coalesce(r.episodes, []) AS episodes
    """
    if limit is not None:
        query += "\n    LIMIT $limit"

    rows: List[EdgeRow] = []
    with driver.session(database=database) as session:
        params: Dict[str, Any] = {"rel_names": [name.lower() for name in rel_names]}
        if limit is not None:
            params["limit"] = limit
        for rec in session.run(query, **params):
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
                    source_labels=[str(x) for x in (rec["source_labels"] or []) if x],
                    target_labels=[str(x) for x in (rec["target_labels"] or []) if x],
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
