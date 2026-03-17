"""Shared Streamlit style block."""

APP_STYLE = r"""
<style>
header[data-testid="stHeader"] {
  display: none !important;
}
[data-testid="stToolbar"] {
  display: none !important;
}
#MainMenu, footer {
  visibility: hidden !important;
}
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
  height: 100vh !important;
  overflow: hidden !important;
}
[data-testid="stAppViewContainer"] {
  top: 0 !important;
}
[data-testid="stMainBlockContainer"] {
  max-width: 100% !important;
  padding: 0 !important;
  margin: 0 !important;
  height: 100vh !important;
  overflow: hidden !important;
}
[data-testid="stVerticalBlock"] {
  gap: 0 !important;
}
[data-testid="stComponent"] {
  height: 100vh !important;
  overflow: hidden !important;
}
[data-testid="stComponent"] iframe {
  height: 100vh !important;
  width: 100% !important;
  border: 0 !important;
  overflow: hidden !important;
}
[data-testid="stSidebar"] div[data-testid="stButton"] {
  margin-top: 10px !important;
  margin-bottom: 6px !important;
}
[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] {
  background: #ffffff !important;
  color: #1f2937 !important;
  border: 1px solid #cfd6df !important;
  border-radius: 8px !important;
  padding: 0.1rem 0.65rem !important;
  height: 32px !important;
  min-height: 32px !important;
  line-height: 1 !important;
  font-weight: 600 !important;
}
[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]:hover {
  background: #f4f7fb !important;
  border-color: #b8c2cf !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] {
  background: #ffedd5 !important;
  border-color: #fdba74 !important;
  color: #9a3412 !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] * {
  color: #9a3412 !important;
}
[data-testid="stSidebar"] {
  transform: none !important;
  visibility: visible !important;
}
[data-testid="stSidebar"][aria-expanded="false"] {
  min-width: 21rem !important;
  max-width: 21rem !important;
}
[data-testid="stSidebar"] > div:first-child {
  width: 21rem !important;
  min-width: 21rem !important;
}
[data-testid="stSidebarCollapseButton"] {
  display: none !important;
}
[data-testid="stSidebarCollapsedControl"] {
  display: none !important;
}
</style>
"""
