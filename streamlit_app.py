import importlib
import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from app_config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from data_access import (
    fetch_nodes,
    fetch_edges,
    fetch_episodes_and_mentions,
    load_demo_dataset,
    load_source_documents,
)
from llm_filter import interpret_filter_query, resolve_node_mention
from timeline_model import (
    apply_filter_spec,
    collect_edge_labels,
    collect_node_kinds,
    collect_node_labels,
    compute_timestep_states,
    format_edge_label,
    format_node_kind_label,
)
from ui_styles import APP_STYLE
import visual_component as visual_component_module


DEMO_DATA_PATH = Path(__file__).resolve().parent / "data" / "demo_payload.json"
DEFAULT_REL_LIMIT = 5000


def use_neo4j_runtime() -> bool:
    try:
        return bool(st.secrets.get("USE_NEO4J", False))
    except st.errors.StreamlitSecretNotFoundError:
        return False


def secret_or_env(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, None)
    except st.errors.StreamlitSecretNotFoundError:
        value = None
    return str(value if value is not None else os.getenv(name, default))


def load_graph_source(limit: int) -> tuple[dict, str]:
    if use_neo4j_runtime():
        edges = fetch_edges(
            uri=NEO4J_URI,
            user=NEO4J_USER,
            password=NEO4J_PASSWORD,
            database=NEO4J_DATABASE,
            limit=limit,
        )
        nodes = fetch_nodes(
            uri=NEO4J_URI,
            user=NEO4J_USER,
            password=NEO4J_PASSWORD,
            database=NEO4J_DATABASE,
            limit=limit,
        )
        episode_map, node_to_episode_uuids = fetch_episodes_and_mentions(
            uri=NEO4J_URI,
            user=NEO4J_USER,
            password=NEO4J_PASSWORD,
            database=NEO4J_DATABASE,
        )
        source_docs = load_source_documents()
        return {
            "nodes": nodes,
            "edges": edges,
            "episode_map": episode_map,
            "node_to_episode_uuids": node_to_episode_uuids,
            "source_docs": source_docs,
        }, "neo4j"

    if not DEMO_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Demo dataset not found at {DEMO_DATA_PATH}. "
            "Generate it with export_demo_payload.py or enable Neo4j via Streamlit secrets."
        )

    nodes, edges, episode_map, node_to_episode_uuids, source_docs = load_demo_dataset(DEMO_DATA_PATH)
    return {
        "nodes": nodes,
        "edges": edges,
        "episode_map": episode_map,
        "node_to_episode_uuids": node_to_episode_uuids,
        "source_docs": source_docs,
    }, "demo"


st.set_page_config(
    page_title="Temporal KG Timeline (Neo4j + D3)",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(APP_STYLE, unsafe_allow_html=True)

if "timeline_granularity" not in st.session_state:
    st.session_state.timeline_granularity = "Year"

granularity = st.session_state.timeline_granularity
next_granularity = "Month" if granularity == "Year" else "Year"
if st.button(
    f"{granularity}: switch to {next_granularity}",
    key="timeline_granularity_toggle",
):
    st.session_state.timeline_granularity = next_granularity
    granularity = next_granularity

st.markdown(
    """
    <style>
    [data-testid="stMain"] div[data-testid="stButton"] {
      position: fixed;
      top: 4px;
      right: 304px;
      z-index: 100000;
      width: auto !important;
    }
    [data-testid="stMain"] div[data-testid="stButton"] > button {
      border: 1px solid #6e7a8f !important;
      border-radius: 6px !important;
      background: #102033 !important;
      color: #dce6f1 !important;
      font-size: 11px !important;
      line-height: 1 !important;
      padding: 4px 10px !important;
      min-height: 0 !important;
      height: 23px !important;
      font-family: sans-serif !important;
      box-sizing: border-box !important;
    }
    #filter-panel-toggle {
      display: none;
    }
    .app-filter-control {
      position: fixed;
      top: 104px;
      left: 12px;
      z-index: 100000;
      border: 1px solid #cfcfcf;
      border-radius: 8px;
      background: #ffffff;
      color: #111827;
      font-size: 12px;
      line-height: 1;
      font-family: sans-serif;
      padding: 8px 10px;
      cursor: pointer;
    }
    .app-filter-control::after {
      content: "Show Filters";
    }
    body:has(#filter-panel-toggle:checked) .app-filter-control {
      left: 348px;
    }
    body:has(#filter-panel-toggle:checked) .app-filter-control::after {
      content: "Hide Filters";
    }
    [data-testid="stSidebar"] {
      display: none !important;
    }
    body:has(#filter-panel-toggle:checked) [data-testid="stSidebar"] {
      display: block !important;
    }
    </style>
    <input id="filter-panel-toggle" type="checkbox" />
    <label class="app-filter-control" for="filter-panel-toggle"></label>
    """,
    unsafe_allow_html=True,
)

if "graph_source" not in st.session_state:
    st.session_state.graph_source = None
    st.session_state.graph_source_mode = None
    st.session_state.payload = None
    st.session_state.raw_payload = None
    st.session_state.labels = []
    st.session_state.edges_loaded = 0
    st.session_state.last_granularity = None
    st.session_state.last_limit = None
    st.session_state.payload_by_granularity = {}
    st.session_state.llm_filter_intent = None
    st.session_state.llm_filter_candidates = {}
    st.session_state.llm_filter_spec = None
    st.session_state.pending_filter_widget_values = None

needs_graph_reload = (
    st.session_state.graph_source is None
    or st.session_state.last_limit != DEFAULT_REL_LIMIT
)

if needs_graph_reload:
    source_label = "Neo4j" if use_neo4j_runtime() else "demo dataset"
    with st.spinner(f"Loading graph data from {source_label}..."):
        graph_source, source_mode = load_graph_source(DEFAULT_REL_LIMIT)
    st.session_state.graph_source = graph_source
    st.session_state.graph_source_mode = source_mode
    st.session_state.edges_loaded = len(graph_source["edges"])
    st.session_state.last_limit = DEFAULT_REL_LIMIT
    st.session_state.payload_by_granularity = {}

missing_granularities = [
    option for option in ("Year", "Month")
    if option not in st.session_state.payload_by_granularity
]

if missing_granularities and st.session_state.graph_source is not None:
    with st.spinner("Computing temporal frames..."):
        for option in missing_granularities:
            _, payload = compute_timestep_states(
                st.session_state.graph_source["nodes"],
                st.session_state.graph_source["edges"],
                episode_map=st.session_state.graph_source["episode_map"],
                node_to_episode_uuids=st.session_state.graph_source["node_to_episode_uuids"],
                source_docs=st.session_state.graph_source["source_docs"],
                granularity=option,
            )
            st.session_state.payload_by_granularity[option] = payload

if granularity in st.session_state.payload_by_granularity:
    payload = st.session_state.payload_by_granularity[granularity]
    st.session_state.payload = payload
    st.session_state.raw_payload = payload
    st.session_state.labels = payload.get("labels", [])
    if st.session_state.last_granularity != granularity:
        st.session_state.last_granularity = granularity
        st.session_state.llm_filter_intent = None
        st.session_state.llm_filter_candidates = {}
        st.session_state.llm_filter_spec = None
        st.session_state.pending_filter_widget_values = None

if st.session_state.raw_payload:
    pending_filter_widget_values = st.session_state.get("pending_filter_widget_values")
    if pending_filter_widget_values:
        for key, value in pending_filter_widget_values.items():
            st.session_state[key] = value
        st.session_state.pending_filter_widget_values = None

    with st.sidebar:
        node_label_options = collect_node_labels(st.session_state.raw_payload)
        node_kind_options = collect_node_kinds(st.session_state.raw_payload)
        edge_label_options = collect_edge_labels(st.session_state.raw_payload)
        st.subheader("Graph Filter")
        selected_node_labels = st.multiselect(
            "Search and select node(s)",
            options=node_label_options,
            default=[],
            key="node_filter_labels",
            help="Selected nodes act as seeds for the relationship mode below.",
        )
        selected_node_kinds = st.multiselect(
            "Filter by node type(s)",
            options=node_kind_options,
            default=[],
            format_func=format_node_kind_label,
            key="node_filter_kinds",
            help="Restricts result nodes by type. Selected seed nodes can still be preserved with the option below.",
        )
        selected_edge_labels = st.multiselect(
            "Filter by edge type(s)",
            options=edge_label_options,
            default=[],
            format_func=format_edge_label,
            key="edge_filter_labels",
            help="Restricts which relationships can be traversed and displayed.",
        )
        relationship_mode = st.selectbox(
            "Selected-node relationship mode",
            options=[
                "union",
                "intersection",
                "path",
                "selected_only",
            ],
            format_func=lambda mode: {
                "union": "Connected to any selected node",
                "intersection": "Connected to all selected nodes",
                "path": "Path between selected nodes",
                "selected_only": "Selected nodes only",
            }[mode],
            key="relationship_filter_mode",
            help="Controls how multiple selected nodes are combined.",
        )
        hop_depth = st.number_input(
            "Hop depth",
            min_value=0,
            max_value=5,
            value=1,
            step=1,
            key="filter_hop_depth",
            help="How many relationship steps to expand from selected nodes.",
        )
        include_seed_nodes = st.checkbox(
            "Always show selected nodes",
            value=True,
            key="filter_include_seed_nodes",
            help="Keeps selected nodes visible even when node type filters would otherwise hide them.",
        )

        st.subheader("AI Filter")
        llm_query = st.text_area(
            "Query",
            key="llm_filter_query",
            placeholder='Example: "In what games did Haaland and Mbappe both play?"',
            height=82,
            label_visibility="collapsed",
        )
        col_interpret, col_clear = st.columns(2)
        with col_interpret:
            interpret_clicked = st.button("Interpret query", key="llm_filter_interpret")
        with col_clear:
            clear_llm_clicked = st.button("Clear LLM filter", key="llm_filter_clear")

        if clear_llm_clicked:
            st.session_state.llm_filter_intent = None
            st.session_state.llm_filter_candidates = {}
            st.session_state.llm_filter_spec = None

        if interpret_clicked:
            if not llm_query.strip():
                st.warning("Enter a filter query first.")
            else:
                try:
                    with st.spinner("Interpreting query..."):
                        intent = interpret_filter_query(
                            llm_query,
                            node_kinds=node_kind_options,
                            edge_labels=edge_label_options,
                            time_labels=[str(label) for label in st.session_state.raw_payload.get("labels", [])],
                            api_key=secret_or_env("DEEPSEEK_API_KEY"),
                            model=secret_or_env("DEEPSEEK_MODEL", "deepseek-chat"),
                            base_url=secret_or_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
                        )
                    st.session_state.llm_filter_intent = intent
                    st.session_state.llm_filter_candidates = {
                        mention: resolve_node_mention(mention, node_label_options)
                        for mention in intent.get("seed_node_mentions", [])
                    }
                    st.session_state.llm_filter_spec = None
                except Exception as exc:
                    st.error(f"Could not interpret query: {exc}")

        if st.session_state.llm_filter_intent:
            intent = st.session_state.llm_filter_intent
            st.caption("Interpreted filter")
            st.json(
                {
                    "node_mentions": intent.get("seed_node_mentions", []),
                    "node_types": intent.get("selected_kinds", []),
                    "edge_types": intent.get("selected_edge_labels", []),
                    "relationship_mode": intent.get("relationship_mode", "union"),
                    "hop_depth": intent.get("hop_depth", 1),
                    "time_range_detected": [
                        intent.get("time_start_label"),
                        intent.get("time_end_label"),
                    ],
                    "note": "When applied, the detected time range is used to fit the timeline to that span.",
                },
                expanded=False,
            )

            resolved_labels = []
            unresolved = []
            for mention_idx, mention in enumerate(intent.get("seed_node_mentions", [])):
                candidates = st.session_state.llm_filter_candidates.get(mention, [])
                labels = [candidate.label for candidate in candidates]
                if not labels:
                    unresolved.append(mention)
                    st.warning(f'No node match found for "{mention}".')
                    continue
                choice = st.selectbox(
                    f'Resolve "{mention}"',
                    options=labels,
                    key=f"llm_resolve_{mention_idx}",
                )
                resolved_labels.append(choice)

            if st.button("Apply interpreted filter", key="llm_filter_apply", disabled=bool(unresolved)):
                st.session_state.llm_filter_spec = {
                    "selected_labels": resolved_labels,
                    "selected_kinds": intent.get("selected_kinds", []),
                    "selected_edge_labels": intent.get("selected_edge_labels", []),
                    "relationship_mode": intent.get("relationship_mode", "union"),
                    "hop_depth": int(intent.get("hop_depth", 1)),
                    "include_seed_nodes": bool(intent.get("include_seed_nodes", True)),
                    "time_start_label": intent.get("time_start_label"),
                    "time_end_label": intent.get("time_end_label"),
                }
                st.session_state.pending_filter_widget_values = {
                    "node_filter_labels": resolved_labels,
                    "node_filter_kinds": intent.get("selected_kinds", []),
                    "edge_filter_labels": intent.get("selected_edge_labels", []),
                    "relationship_filter_mode": intent.get("relationship_mode", "union"),
                    "filter_hop_depth": int(intent.get("hop_depth", 1)),
                    "filter_include_seed_nodes": bool(intent.get("include_seed_nodes", True)),
                }
                st.rerun()
    filter_spec = {
        "selected_labels": selected_node_labels,
        "selected_kinds": selected_node_kinds,
        "selected_edge_labels": selected_edge_labels,
        "relationship_mode": relationship_mode,
        "hop_depth": int(hop_depth),
        "include_seed_nodes": include_seed_nodes,
        "time_start_label": None,
        "time_end_label": None,
    }
    if st.session_state.llm_filter_spec:
        filter_spec = st.session_state.llm_filter_spec
        with st.sidebar:
            st.info("Using the applied LLM filter. Clear it to return to manual filters.")
            if filter_spec.get("time_start_label") or filter_spec.get("time_end_label"):
                st.caption(
                    "LLM time range: "
                    f"{filter_spec.get('time_start_label') or 'start'} "
                    f"to {filter_spec.get('time_end_label') or 'end'}"
                )
    initial_time_window = {
        "start_label": filter_spec.get("time_start_label"),
        "end_label": filter_spec.get("time_end_label"),
    }
    structural_filter_spec = dict(filter_spec)
    structural_filter_spec["time_start_label"] = None
    structural_filter_spec["time_end_label"] = None
    st.session_state.payload = apply_filter_spec(st.session_state.raw_payload, structural_filter_spec)
else:
    initial_time_window = None

if not st.session_state.payload or not st.session_state.labels:
    st.info("Load data to see the timeline visualization.")
else:
    vc_module = importlib.reload(visual_component_module)
    html = vc_module.d3_html(
        st.session_state.payload,
        0,
        width=1380,
        height=780,
        initial_time_window=initial_time_window,
    )
    components.html(html, height=1000, scrolling=False)
