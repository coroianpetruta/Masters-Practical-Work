from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from app_config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from data_access import (
    fetch_edges,
    fetch_episodes_and_mentions,
    load_demo_dataset,
    load_source_documents,
)
from timeline_model import apply_node_filter, collect_node_labels, compute_timestep_states
from ui_styles import APP_STYLE
from visual_component import d3_html


DEMO_DATA_PATH = Path(__file__).resolve().parent / "data" / "demo_payload.json"
DEFAULT_REL_LIMIT = 5000


def use_neo4j_runtime() -> bool:
    return bool(st.secrets.get("USE_NEO4J", False))


def load_graph_source(limit: int) -> tuple[dict, str]:
    if use_neo4j_runtime():
        edges = fetch_edges(
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

    edges, episode_map, node_to_episode_uuids, source_docs = load_demo_dataset(DEMO_DATA_PATH)
    return {
        "edges": edges,
        "episode_map": episode_map,
        "node_to_episode_uuids": node_to_episode_uuids,
        "source_docs": source_docs,
    }, "demo"


st.set_page_config(page_title="Temporal KG Timeline (Neo4j + D3)", layout="wide")
st.markdown(APP_STYLE, unsafe_allow_html=True)

with st.sidebar:
    st.header("Timeline")
    granularity = st.selectbox("Granularity", ["Year", "Month"], index=0)
    limit = st.number_input(
        "Max relationships to load",
        min_value=1,
        max_value=200000,
        value=DEFAULT_REL_LIMIT,
        step=1000,
    )
    load_btn = st.button("Refresh graph", type="primary")

if "graph_source" not in st.session_state:
    st.session_state.graph_source = None
    st.session_state.graph_source_mode = None
    st.session_state.payload = None
    st.session_state.raw_payload = None
    st.session_state.labels = []
    st.session_state.edges_loaded = 0
    st.session_state.last_granularity = None
    st.session_state.last_limit = None

needs_graph_reload = (
    load_btn
    or st.session_state.graph_source is None
    or st.session_state.last_limit != int(limit)
)

if needs_graph_reload:
    source_label = "Neo4j" if use_neo4j_runtime() else "demo dataset"
    with st.spinner(f"Loading graph data from {source_label}..."):
        graph_source, source_mode = load_graph_source(int(limit))
    st.session_state.graph_source = graph_source
    st.session_state.graph_source_mode = source_mode
    st.session_state.edges_loaded = len(graph_source["edges"])
    st.session_state.last_limit = int(limit)

needs_payload_recompute = (
    needs_graph_reload
    or st.session_state.raw_payload is None
    or st.session_state.last_granularity != granularity
)

if needs_payload_recompute and st.session_state.graph_source is not None:
    with st.spinner("Computing temporal frames..."):
        _, payload = compute_timestep_states(
            st.session_state.graph_source["edges"],
            episode_map=st.session_state.graph_source["episode_map"],
            node_to_episode_uuids=st.session_state.graph_source["node_to_episode_uuids"],
            source_docs=st.session_state.graph_source["source_docs"],
            granularity=granularity,
        )

    st.session_state.payload = payload
    st.session_state.raw_payload = payload
    st.session_state.labels = payload.get("labels", [])
    st.session_state.last_granularity = granularity

if st.session_state.raw_payload:
    with st.sidebar:
        mode_label = "Neo4j" if st.session_state.graph_source_mode == "neo4j" else "Demo dataset"
        st.caption(f"Data source: {mode_label}")
        node_label_options = collect_node_labels(st.session_state.raw_payload)
        st.subheader("Node Filter")
        selected_node_labels = st.multiselect(
            "Search and select node(s)",
            options=node_label_options,
            default=[],
            key="node_filter_labels",
            help="Shows only selected node(s) and directly connected neighbors via selected-node edges.",
        )
    st.session_state.payload = apply_node_filter(st.session_state.raw_payload, selected_node_labels)

if not st.session_state.payload or not st.session_state.labels:
    st.info("Load data to see the timeline visualization.")
else:
    html = d3_html(st.session_state.payload, 0, width=1380, height=780)
    components.html(html, height=1000, scrolling=False)
