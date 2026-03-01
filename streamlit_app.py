import streamlit as st
import streamlit.components.v1 as components

from app_config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from data_access import fetch_edges, fetch_episodes_and_mentions, load_source_documents
from timeline_model import apply_node_filter, collect_node_labels, compute_timestep_states
from ui_styles import APP_STYLE
from visual_component import d3_html


st.set_page_config(page_title="Temporal KG Timeline (Neo4j + D3)", layout="wide")
st.markdown(APP_STYLE, unsafe_allow_html=True)

with st.sidebar:
    st.header("Timeline")
    granularity = st.selectbox("Granularity", ["Year", "Month"], index=0)
    limit = st.number_input("Max relationships to load", min_value=1, max_value=200000, value=5000, step=1000)
    load_btn = st.button("Refresh graph", type="primary")

if "payload" not in st.session_state:
    st.session_state.payload = None
    st.session_state.raw_payload = None
    st.session_state.labels = []
    st.session_state.edges_loaded = 0

if load_btn or st.session_state.payload is None:
    with st.spinner("Fetching edges and source mappings from Neo4j..."):
        edges = fetch_edges(
            uri=NEO4J_URI,
            user=NEO4J_USER,
            password=NEO4J_PASSWORD,
            database=NEO4J_DATABASE,
            limit=int(limit),
        )
        episode_map, node_to_episode_uuids = fetch_episodes_and_mentions(
            uri=NEO4J_URI,
            user=NEO4J_USER,
            password=NEO4J_PASSWORD,
            database=NEO4J_DATABASE,
        )
        source_docs = load_source_documents()

    with st.spinner("Computing temporal frames..."):
        _, payload = compute_timestep_states(
            edges,
            episode_map=episode_map,
            node_to_episode_uuids=node_to_episode_uuids,
            source_docs=source_docs,
            granularity=granularity,
        )

    st.session_state.payload = payload
    st.session_state.raw_payload = payload
    st.session_state.labels = payload.get("labels", [])
    st.session_state.edges_loaded = len(edges)

if st.session_state.raw_payload:
    node_label_options = collect_node_labels(st.session_state.raw_payload)
    with st.sidebar:
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
