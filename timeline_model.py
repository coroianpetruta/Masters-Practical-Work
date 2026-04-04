"""Timeline and node-filter model construction."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from data_access import EdgeRow, EpisodeRow, NodeRow
from time_utils import floor_to_bin, make_bins, label_bin

RED_CAPABLE_RELATIONS = {
    "player_plays_for_team",
    "coach_manages_team",
    "stadium_home_of_team",
    "team_participates_in_competition",
    "transfer_event_to_team",
    "transfer_event_from_team",
}


def normalized_rel_name(rel_name: str) -> str:
    return str(rel_name or "").strip().lower()


def relation_can_turn_invalid(rel_name: str) -> bool:
    return normalized_rel_name(rel_name) in RED_CAPABLE_RELATIONS


def infer_node_kind(rel_name: str, is_source: bool) -> str:
    name = normalized_rel_name(rel_name)
    if "player" in name and "team" in name:
        return "player" if is_source else "team"
    if "player" in name:
        return "player" if is_source else "entity"
    if "team" in name:
        return "team"
    return "entity"


def merge_node_kind(current: Optional[str], new_kind: str) -> str:
    if not current or current == "entity":
        return new_kind
    if new_kind == "entity" or current == new_kind:
        return current
    return "entity"


def kind_from_labels(labels: List[str]) -> Optional[str]:
    lowered = [
        str(lbl).lower()
        for lbl in labels
        if str(lbl).lower() not in {"entity", "episodic", "community", "saga"}
    ]
    if any("player" in lbl for lbl in lowered):
        return "player"
    if any("team" in lbl for lbl in lowered):
        return "team"
    if any("coach" in lbl for lbl in lowered):
        return "coach"
    if lowered:
        return lowered[0]
    return None

def edge_start_dt(e: EdgeRow) -> Optional[datetime]:
    return e.valid_at or e.created_at


def compute_timestep_states(
    nodes: List[NodeRow],
    edges: List[EdgeRow],
    episode_map: Dict[str, EpisodeRow],
    node_to_episode_uuids: Dict[str, Set[str]],
    source_docs: Dict[str, Dict[str, str]],
    granularity: str,
) -> Tuple[List[datetime], Dict[str, Any]]:
    """
    Produces:
      - bins: list of bin starts
      - frames: per-bin dict with nodes + links + status {new/active/invalid}
    """
    # Filter edges that have some start time; otherwise they can’t be placed.
    usable_nodes = [n for n in nodes if n.created_at is not None]
    usable = [e for e in edges if edge_start_dt(e) is not None]
    if not usable and not usable_nodes:
        return [], {"frames": [], "labels": [], "episodes": {}, "sources": {}}

    starts = [edge_start_dt(e) for e in usable if edge_start_dt(e) is not None]
    starts.extend(n.created_at for n in usable_nodes if n.created_at is not None)
    ends = []
    for e in usable:
        # if invalid_at exists, include it in range
        if e.invalid_at is not None:
            ends.append(e.invalid_at)
        else:
            ends.append(edge_start_dt(e))
    ends.extend(n.created_at for n in usable_nodes if n.created_at is not None)
    min_dt = min(starts)
    max_dt = max(ends)

    bins = make_bins(min_dt, max_dt, granularity)
    labels = [label_bin(b, granularity) for b in bins]

    # Precompute per-edge bins
    start_bin = {e.edge_id: floor_to_bin(edge_start_dt(e), granularity) for e in usable}
    invalid_bin = {
        e.edge_id: (
            floor_to_bin(e.invalid_at, granularity)
            if e.invalid_at and relation_can_turn_invalid(e.rel_name)
            else None
        )
        for e in usable
    }
    invalid_idx = {
        e.edge_id: (bins.index(invalid_bin[e.edge_id]) if invalid_bin[e.edge_id] is not None else None)
        for e in usable
    }
    label_map: Dict[str, str] = {}
    node_kind_map: Dict[str, str] = {}
    node_first_seen: Dict[str, datetime] = {}
    node_incident_edges: Dict[str, List[EdgeRow]] = {}
    for n in usable_nodes:
        label_map[n.node_id] = n.label
        node_kind_map[n.node_id] = kind_from_labels(n.labels) or "entity"
        node_first_seen[n.node_id] = n.created_at
    for e in usable:
        label_map[e.source_id] = e.source_label
        label_map[e.target_id] = e.target_label
        source_kind = kind_from_labels(e.source_labels) or infer_node_kind(e.rel_name, True)
        target_kind = kind_from_labels(e.target_labels) or infer_node_kind(e.rel_name, False)
        node_kind_map[e.source_id] = merge_node_kind(node_kind_map.get(e.source_id), source_kind)
        node_kind_map[e.target_id] = merge_node_kind(node_kind_map.get(e.target_id), target_kind)
        node_incident_edges.setdefault(e.source_id, []).append(e)
        node_incident_edges.setdefault(e.target_id, []).append(e)
        sb = start_bin[e.edge_id]
        for nid in (e.source_id, e.target_id):
            if nid not in node_first_seen or sb < node_first_seen[nid]:
                node_first_seen[nid] = sb

    # Serialize sources and episodes once for frontend panel/highlighting
    episodes_payload: Dict[str, Dict[str, Any]] = {}
    for ep_uuid, ep in episode_map.items():
        episodes_payload[ep_uuid] = {
            "uuid": ep_uuid,
            "source_text_name": ep.source_text_name,
            "context": ep.context,
            "created_at": ep.created_at.isoformat().replace("+00:00", "Z") if ep.created_at else None,
        }

    sources_payload: Dict[str, Dict[str, Any]] = {}
    for name, data in source_docs.items():
        sources_payload[name] = {
            "name": name,
            "date_accessed": data.get("date_accessed", ""),
            "link": data.get("link", ""),
            "text": data.get("text", ""),
        }

    # For each timestep, determine:
    # - edges shown: all that have started and not yet invalidated before this bin
    # - edges colored:
    #    green if start_bin == this_bin
    #    red if invalid_bin == this_bin
    #    gray otherwise (active)
    # If invalid_bin == this_bin: show red this timestep, remove next.
    frames = []
    previous_invalid_nodes: Set[str] = set()
    node_invalid_start_idx: Dict[str, int] = {}
    for b_idx, b in enumerate(bins):
        visible_edges: List[EdgeRow] = []
        active_node_ids: Set[str] = set()
        for e in usable:
            sb = start_bin[e.edge_id]
            ib = invalid_bin[e.edge_id]
            if sb > b:
                continue
            visible_edges.append(e)
            if ib is None or ib > b:
                active_node_ids.add(e.source_id)
                active_node_ids.add(e.target_id)

        node_ids = {nid for nid, first_seen in node_first_seen.items() if first_seen <= b}
        current_invalid_nodes = {
            nid for nid in node_ids if nid not in active_node_ids and node_incident_edges.get(nid)
        }
        prior_invalid_nodes = set(previous_invalid_nodes)

        for nid in current_invalid_nodes:
            if nid not in prior_invalid_nodes:
                node_invalid_start_idx[nid] = b_idx
        previous_invalid_nodes = current_invalid_nodes

        nodes = []
        for nid in sorted(node_ids):
            is_new = node_first_seen.get(nid) == b
            is_invalid_event = nid in current_invalid_nodes and nid not in prior_invalid_nodes
            is_currently_invalid = nid in current_invalid_nodes
            status = "active"
            if is_new and is_currently_invalid:
                status = "new_invalid"
            elif is_new:
                status = "new"
            elif is_currently_invalid:
                status = "invalid"
            invalid_age = (
                b_idx - node_invalid_start_idx[nid]
                if is_currently_invalid and nid in node_invalid_start_idx
                else None
            )
            ep_uuids = sorted(node_to_episode_uuids.get(nid, set()))
            nodes.append(
                {
                    "id": nid,
                    "label": label_map.get(nid, nid),
                    "kind": node_kind_map.get(nid, "entity"),
                    "status": status,
                    "is_new": is_new,
                    "is_invalid": is_invalid_event,
                    "invalid_age": invalid_age,
                    "episode_uuids": ep_uuids,
                }
            )

        links = []
        for e in visible_edges:
            is_new = start_bin[e.edge_id] == b
            is_invalid_event = invalid_bin[e.edge_id] == b
            is_currently_invalid = invalid_bin[e.edge_id] is not None and invalid_bin[e.edge_id] <= b
            status = "active"
            if is_new and is_currently_invalid:
                status = "new_invalid"
            elif is_new:
                status = "new"
            elif is_currently_invalid:
                status = "invalid"
            age = (
                b_idx - invalid_idx[e.edge_id]
                if is_currently_invalid and invalid_idx[e.edge_id] is not None
                else None
            )
            links.append(
                {
                    "id": e.edge_id,
                    "source": e.source_id,
                    "target": e.target_id,
                    "label": e.rel_name,
                    "status": status,
                    "is_new": is_new,
                    "is_invalid": is_invalid_event,
                    "invalid_age": age,
                    "episode_uuids": sorted(set(e.episode_uuids)),
                }
            )

        visible_doc_names: Set[str] = set()
        # Tabs should reflect documents that CREATED graph elements in this timestep.
        for n in nodes:
            if n.get("status") not in ("new", "new_invalid"):
                continue
            for ep_uuid in n.get("episode_uuids", []):
                ep = episode_map.get(ep_uuid)
                if ep and ep.source_text_name:
                    visible_doc_names.add(ep.source_text_name)
        for l in links:
            if l.get("status") not in ("new", "new_invalid"):
                continue
            for ep_uuid in l.get("episode_uuids", []):
                ep = episode_map.get(ep_uuid)
                if ep and ep.source_text_name:
                    visible_doc_names.add(ep.source_text_name)

        ordered_doc_names = sorted(
            visible_doc_names,
            key=lambda n: (sources_payload.get(n, {}).get("date_accessed", "9999-12-31"), n),
        )

        frames.append({"nodes": nodes, "links": links, "doc_names": ordered_doc_names})

    return bins, {
        "frames": frames,
        "labels": labels,
        "episodes": episodes_payload,
        "sources": sources_payload,
        "granularity": granularity,
    }


def collect_node_labels(payload: Dict[str, Any]) -> List[str]:
    labels: Set[str] = set()
    for frame in payload.get("frames", []):
        for n in frame.get("nodes", []):
            label = str(n.get("label", "")).strip()
            if label:
                labels.add(label)
    return sorted(labels)


NODE_KIND_LABELS = {
    "player": "Player",
    "team": "Team",
    "coach": "Coach",
    "match": "Match",
    "competition": "Competition",
    "goalevent": "GoalEvent",
    "injuryevent": "InjuryEvent",
    "transferevent": "TransferEvent",
    "retirementevent": "RetirementEvent",
    "award": "Award",
    "record": "Record",
    "stadium": "Stadium",
    "entity": "Entity",
}


def collect_node_kinds(payload: Dict[str, Any]) -> List[str]:
    kinds: Set[str] = set()
    for frame in payload.get("frames", []):
        for n in frame.get("nodes", []):
            kind = str(n.get("kind", "")).strip().lower()
            if kind:
                kinds.add(kind)
    return sorted(kinds, key=lambda kind: NODE_KIND_LABELS.get(kind, kind).lower())


def format_node_kind_label(kind: str) -> str:
    return NODE_KIND_LABELS.get(str(kind).strip().lower(), str(kind))


def apply_node_filter(
    payload: Dict[str, Any],
    selected_labels: List[str],
    selected_kinds: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Keep:
    - if only node kinds are selected: all nodes of selected kinds
    - if explicit nodes are selected: all explicitly selected nodes
    - if explicit nodes are selected: only direct neighbors of those nodes
      and, when selected kinds exist, only neighbors whose type is selected
    Recompute node statuses on the filtered subgraph timeline.
    """
    if not selected_labels and not selected_kinds:
        return payload

    frames = payload.get("frames", [])
    labels = payload.get("labels", [])
    episodes = payload.get("episodes", {})
    sources = payload.get("sources", {})
    granularity = payload.get("granularity", "")
    selected_label_set = set(selected_labels)
    selected_kind_set = {str(kind).strip().lower() for kind in (selected_kinds or []) if str(kind).strip()}

    # selected node ids come from the full timeline graph
    selected_ids: Set[str] = set()
    kind_selected_ids: Set[str] = set()
    label_by_id: Dict[str, str] = {}
    kind_by_id: Dict[str, str] = {}
    for frame in frames:
        for n in frame.get("nodes", []):
            nid = str(n.get("id"))
            nlabel = str(n.get("label", nid))
            nkind = str(n.get("kind", "entity")).strip().lower()
            label_by_id[nid] = nlabel
            kind_by_id[nid] = nkind
            if nlabel in selected_label_set:
                selected_ids.add(nid)
            if nkind in selected_kind_set:
                kind_selected_ids.add(nid)

    if not selected_ids and not kind_selected_ids:
        return {"frames": [], "labels": labels, "episodes": episodes, "sources": sources, "granularity": granularity}

    filtered_frame_links: List[List[Dict[str, Any]]] = []
    frame_node_ids: List[Set[str]] = []

    for frame in frames:
        orig_nodes = frame.get("nodes", [])
        orig_links = frame.get("links", [])
        orig_node_ids = {str(n.get("id")) for n in orig_nodes}

        keep_links: List[Dict[str, Any]] = []
        keep_node_ids: Set[str] = set()

        if selected_ids:
            # Explicit node filter drives the subgraph. Node kinds, when present,
            # constrain which neighbor types may appear around the selected nodes.
            for l in orig_links:
                s = str(l.get("source"))
                t = str(l.get("target"))

                neighbor_id = None
                if s in selected_ids and t not in selected_ids:
                    neighbor_id = t
                elif t in selected_ids and s not in selected_ids:
                    neighbor_id = s
                elif s in selected_ids and t in selected_ids:
                    neighbor_id = None
                else:
                    continue

                if selected_kind_set and neighbor_id is not None:
                    if kind_by_id.get(neighbor_id, "entity") not in selected_kind_set:
                        continue

                keep_links.append(dict(l))
                keep_node_ids.add(s)
                keep_node_ids.add(t)

            # Keep explicit selected nodes even if isolated after filtering.
            keep_node_ids.update({nid for nid in selected_ids if nid in orig_node_ids})
        else:
            # Only node-kind filtering: show the full induced subgraph on those kinds.
            for l in orig_links:
                s = str(l.get("source"))
                t = str(l.get("target"))
                if s in kind_selected_ids and t in kind_selected_ids:
                    keep_links.append(dict(l))
                    keep_node_ids.add(s)
                    keep_node_ids.add(t)
            keep_node_ids.update({nid for nid in kind_selected_ids if nid in orig_node_ids})

        filtered_frame_links.append(keep_links)
        frame_node_ids.append(keep_node_ids)

    # First seen for filtered subgraph
    first_seen_idx: Dict[str, int] = {}
    for i, ids in enumerate(frame_node_ids):
        for nid in ids:
            if nid not in first_seen_idx:
                first_seen_idx[nid] = i

    filtered_frames: List[Dict[str, Any]] = []
    previous_invalid_nodes: Set[str] = set()
    node_invalid_start_idx: Dict[str, int] = {}
    for i, keep_links in enumerate(filtered_frame_links):
        ids_now = frame_node_ids[i]
        active_node_ids: Set[str] = set()
        for l in keep_links:
            if l.get("status") in ("active", "new"):
                active_node_ids.add(str(l.get("source")))
                active_node_ids.add(str(l.get("target")))

        linked_node_ids = {str(l.get("source")) for l in keep_links} | {str(l.get("target")) for l in keep_links}
        current_invalid_nodes = {nid for nid in ids_now if nid not in active_node_ids and nid in linked_node_ids}
        prior_invalid_nodes = set(previous_invalid_nodes)
        for nid in current_invalid_nodes:
            if nid not in prior_invalid_nodes:
                node_invalid_start_idx[nid] = i
        previous_invalid_nodes = current_invalid_nodes

        nodes_out: List[Dict[str, Any]] = []
        for nid in sorted(ids_now):
            is_new = first_seen_idx.get(nid) == i
            is_invalid_event = nid in current_invalid_nodes and nid not in prior_invalid_nodes
            is_currently_invalid = nid in current_invalid_nodes
            status = "active"
            if is_new and is_currently_invalid:
                status = "new_invalid"
            elif is_new:
                status = "new"
            elif is_currently_invalid:
                status = "invalid"

            # preserve episode uuids from original frame node if available
            ep_uuids: List[str] = []
            for n in frames[i].get("nodes", []):
                if str(n.get("id")) == nid:
                    ep_uuids = list(n.get("episode_uuids", []))
                    break

            nodes_out.append(
                {
                    "id": nid,
                    "label": label_by_id.get(nid, nid),
                    "kind": kind_by_id.get(nid, "entity"),
                    "status": status,
                    "is_new": is_new,
                    "is_invalid": is_invalid_event,
                    "invalid_age": (
                        i - node_invalid_start_idx[nid]
                        if is_currently_invalid and nid in node_invalid_start_idx
                        else None
                    ),
                    "episode_uuids": ep_uuids,
                }
            )

        # Recompute docs for this filtered frame from created (new/new_invalid) elements.
        visible_doc_names: Set[str] = set()
        for n in nodes_out:
            if n.get("status") not in ("new", "new_invalid"):
                continue
            for ep_uuid in n.get("episode_uuids", []):
                ep = episodes.get(ep_uuid)
                if ep and ep.get("source_text_name"):
                    visible_doc_names.add(str(ep.get("source_text_name")))

        links_out: List[Dict[str, Any]] = []
        for l in keep_links:
            links_out.append(dict(l))
            if l.get("status") in ("new", "new_invalid"):
                for ep_uuid in l.get("episode_uuids", []):
                    ep = episodes.get(ep_uuid)
                    if ep and ep.get("source_text_name"):
                        visible_doc_names.add(str(ep.get("source_text_name")))

        ordered_doc_names = sorted(
            visible_doc_names,
            key=lambda n: (sources.get(n, {}).get("date_accessed", "9999-12-31"), n),
        )

        filtered_frames.append({"nodes": nodes_out, "links": links_out, "doc_names": ordered_doc_names})

    return {
        "frames": filtered_frames,
        "labels": labels,
        "episodes": episodes,
        "sources": sources,
        "granularity": granularity,
    }
