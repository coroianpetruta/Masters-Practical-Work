from pathlib import Path

from app_config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from data_access import (
    fetch_nodes,
    fetch_edges,
    fetch_episodes_and_mentions,
    load_source_documents,
    save_demo_dataset,
)


OUTPUT_PATH = Path(__file__).resolve().parent / "data" / "demo_payload.json"
def main() -> None:
    nodes = fetch_nodes(
        uri=NEO4J_URI,
        user=NEO4J_USER,
        password=NEO4J_PASSWORD,
        database=NEO4J_DATABASE,
        limit=None,
    )
    edges = fetch_edges(
        uri=NEO4J_URI,
        user=NEO4J_USER,
        password=NEO4J_PASSWORD,
        database=NEO4J_DATABASE,
        limit=None,
    )
    episode_map, node_to_episode_uuids = fetch_episodes_and_mentions(
        uri=NEO4J_URI,
        user=NEO4J_USER,
        password=NEO4J_PASSWORD,
        database=NEO4J_DATABASE,
    )
    source_docs = load_source_documents()

    save_demo_dataset(
        OUTPUT_PATH,
        nodes=nodes,
        edges=edges,
        episode_map=episode_map,
        node_to_episode_uuids=node_to_episode_uuids,
        source_docs=source_docs,
    )
    print(f"Wrote demo dataset to {OUTPUT_PATH}")
    print(f"Nodes: {len(nodes)}")
    print(f"Edges: {len(edges)}")
    print(f"Episodes: {len(episode_map)}")
    print(f"Nodes with episode links: {len(node_to_episode_uuids)}")


if __name__ == "__main__":
    main()
