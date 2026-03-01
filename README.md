# Graphiti Experiments

This project contains:
- A Streamlit app to explore a temporal knowledge graph timeline.
- Jupyter notebooks to update/prepare graph data in Neo4j.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run Streamlit App

From the project root:

```bash
streamlit run practical_work/streamlit_app.py
```

Neo4j connection settings are defined in:
- `practical_work/app_config.py`

## Run Notebook Updates

Open Jupyter:

```bash
jupyter notebook
```

Then run notebooks in `practical_work/`:
- `database_update.ipynb`
- `database_update_created_at.ipynb`

## Data Files

Source files used by the app/notebooks are in:
- `practical_work/data/`
