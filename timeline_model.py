"""Timeline and node-filter model construction."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from data_access import EdgeRow, EpisodeRow
from time_utils import floor_to_bin, make_bins, next_bin_start, label_bin

def edge_start_dt(e: EdgeRow) -> Optional[datetime]:
    return e.valid_at or e.created_at


def compute_timestep_states(
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
    usable = [e for e in edges if edge_start_dt(e) is not None]
    if not usable:
        return [], {"frames": [], "labels": [], "episodes": {}, "sources": {}}

    starts = [edge_start_dt(e) for e in usable if edge_start_dt(e) is not None]
    ends = []
    for e in usable:
        # if invalid_at exists, include it in range
        if e.invalid_at is not None:
            ends.append(e.invalid_at)
        else:
            ends.append(edge_start_dt(e))
    min_dt = min(starts)
    max_dt = max(ends)

    bins = make_bins(min_dt, max_dt, granularity)
    labels = [label_bin(b, granularity) for b in bins]

    # Precompute per-edge bins
    start_bin = {e.edge_id: floor_to_bin(edge_start_dt(e), granularity) for e in usable}
    invalid_bin = {e.edge_id: (floor_to_bin(e.invalid_at, granularity) if e.invalid_at else None) for e in usable}

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
    for b in bins:
        # edges visible at bin b:
        visible_edges: List[EdgeRow] = []
        for e in usable:
            sb = start_bin[e.edge_id]
            ib = invalid_bin[e.edge_id]
            if sb > b:
                continue
            # if invalidated in an earlier bin, it's gone
            if ib is not None and ib < b:
                continue
            # if invalidated in this bin, still visible (red)
            visible_edges.append(e)

        # node activity based on visible edges that are NOT already gone
        node_ids = set()
        for e in visible_edges:
            node_ids.add(e.source_id)
            node_ids.add(e.target_id)

        # Compute node "new" and "invalid" moments:
        # New node = first bin where node appears at all.
        # Invalid node = bin where it loses last active connection (shown red), i.e.,
        #               node exists in this bin but will not exist in next bin.
        # We'll compute this by looking at activity in next bin.
        # First, build node->first_seen_bin from starts of incident edges.
        # For robustness, node first seen is min start_bin of incident edges.
        first_seen: Dict[str, datetime] = {}
        for e in usable:
            sb = start_bin[e.edge_id]
            for nid in (e.source_id, e.target_id):
                if nid not in first_seen or sb < first_seen[nid]:
                    first_seen[nid] = sb

        # Compute node present in next bin for invalid marking
        next_b = next_bin_start(b, granularity)
        # Only relevant if next_b is within range
        in_range_next = next_b <= bins[-1]

        next_node_ids = set()
        if in_range_next:
            for e in usable:
                sb = start_bin[e.edge_id]
                ib = invalid_bin[e.edge_id]
                if sb > next_b:
                    continue
                if ib is not None and ib < next_b:
                    continue
                # if ib == next_b, still visible next step as red
                next_node_ids.add(e.source_id)
                next_node_ids.add(e.target_id)

        # Build nodes with status
        nodes = []
        # create quick label map from any edge
        label_map: Dict[str, str] = {}
        for e in usable:
            label_map[e.source_id] = e.source_label
            label_map[e.target_id] = e.target_label

        for nid in node_ids:
            is_new = first_seen.get(nid) == b
            is_invalid = in_range_next and (nid not in next_node_ids)
            status = "active"
            if is_new and is_invalid:
                status = "new_invalid"
            elif is_new:
                status = "new"
            elif is_invalid:
                status = "invalid"
            ep_uuids = sorted(node_to_episode_uuids.get(nid, set()))
            nodes.append(
                {
                    "id": nid,
                    "label": label_map.get(nid, nid),
                    "status": status,
                    "is_new": is_new,
                    "is_invalid": is_invalid,
                    "episode_uuids": ep_uuids,
                }
            )

        # Build links with status
        links = []
        for e in visible_edges:
            is_new = start_bin[e.edge_id] == b
            is_invalid = invalid_bin[e.edge_id] == b
            status = "active"
            if is_new and is_invalid:
                status = "new_invalid"
            elif is_new:
                status = "new"
            elif is_invalid:
                status = "invalid"
            links.append(
                {
                    "id": e.edge_id,
                    "source": e.source_id,
                    "target": e.target_id,
                    "label": e.rel_name,
                    "status": status,
                    "is_new": is_new,
                    "is_invalid": is_invalid,
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


def apply_node_filter(payload: Dict[str, Any], selected_labels: List[str]) -> Dict[str, Any]:
    """
    Keep only edges directly incident to selected nodes and nodes touched by those edges.
    Recompute node statuses on the filtered subgraph timeline.
    """
    if not selected_labels:
        return payload

    frames = payload.get("frames", [])
    labels = payload.get("labels", [])
    episodes = payload.get("episodes", {})
    sources = payload.get("sources", {})
    granularity = payload.get("granularity", "")
    selected_label_set = set(selected_labels)

    # selected node ids come from the full timeline graph
    selected_ids: Set[str] = set()
    label_by_id: Dict[str, str] = {}
    for frame in frames:
        for n in frame.get("nodes", []):
            nid = str(n.get("id"))
            nlabel = str(n.get("label", nid))
            label_by_id[nid] = nlabel
            if nlabel in selected_label_set:
                selected_ids.add(nid)

    if not selected_ids:
        return {"frames": [], "labels": labels, "episodes": episodes, "sources": sources, "granularity": granularity}

    filtered_frame_links: List[List[Dict[str, Any]]] = []
    frame_node_ids: List[Set[str]] = []
    present_original_ids: List[Set[str]] = []

    for frame in frames:
        orig_nodes = frame.get("nodes", [])
        orig_links = frame.get("links", [])
        orig_node_ids = {str(n.get("id")) for n in orig_nodes}
        present_original_ids.append(orig_node_ids)

        keep_links: List[Dict[str, Any]] = []
        keep_node_ids: Set[str] = set()
        for l in orig_links:
            s = str(l.get("source"))
            t = str(l.get("target"))
            if s in selected_ids or t in selected_ids:
                keep_links.append(dict(l))
                keep_node_ids.add(s)
                keep_node_ids.add(t)

        # Keep selected nodes if they exist this frame, even if isolated after filtering
        keep_node_ids.update({nid for nid in selected_ids if nid in orig_node_ids})
        filtered_frame_links.append(keep_links)
        frame_node_ids.append(keep_node_ids)

    # First seen for filtered subgraph
    first_seen_idx: Dict[str, int] = {}
    for i, ids in enumerate(frame_node_ids):
        for nid in ids:
            if nid not in first_seen_idx:
                first_seen_idx[nid] = i

    filtered_frames: List[Dict[str, Any]] = []
    for i, keep_links in enumerate(filtered_frame_links):
        ids_now = frame_node_ids[i]
        ids_next = frame_node_ids[i + 1] if i + 1 < len(frame_node_ids) else set()

        nodes_out: List[Dict[str, Any]] = []
        for nid in sorted(ids_now):
            is_new = first_seen_idx.get(nid) == i
            is_invalid = nid not in ids_next
            status = "active"
            if is_new and is_invalid:
                status = "new_invalid"
            elif is_new:
                status = "new"
            elif is_invalid:
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
                    "status": status,
                    "is_new": is_new,
                    "is_invalid": is_invalid,
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
