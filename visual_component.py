"""D3 component renderer for Streamlit."""

import json
from typing import Any, Dict

def d3_html(payload: Dict[str, Any], frame_idx: int, width: int = 1380, height: int = 780) -> str:
    data_json = json.dumps(payload)
    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <style>
    html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; font-family: sans-serif; background: #fff; overflow: hidden; }}
    .wrap {{ width: 100%; height: 100%; position: relative; }}
    .layout {{ position: absolute; left: 0; right: 0; top: 94px; bottom: 0; display: flex; }}
    .graph-pane {{ position: relative; flex: 1 1 auto; min-width: 0; border-right: 1px solid #e7e7e7; overflow: hidden; }}
    .source-pane {{ width: 42%; min-width: 380px; max-width: 620px; background: #fafafa; display: flex; flex-direction: column; }}
    .source-pane.hidden {{ display: none; }}

    .timeline-shell {{
      position: absolute; left: 0; right: 0; top: 0; height: 94px;
      z-index: 14; background: #060d1a; border-bottom: 1px solid #1c2a3b;
    }}
    .window-summary {{
      position: absolute; left: 12px; right: 180px; bottom: 4px;
      display: flex; gap: 10px; align-items: center;
      padding: 6px 10px; border-radius: 8px;
      border: 1px solid rgba(92,122,156,0.5);
      background: rgba(6, 13, 26, 0.72);
      color: #d0d9e8; font-size: 11px; line-height: 1.4;
      transition: background 0.15s ease, border-color 0.15s ease;
    }}
    .window-summary:not(.active) {{ opacity: 0.85; }}
    .window-summary-text b {{ color: #fff; }}
    .window-clear-btn {{
      border: 1px solid #6e7a8f; border-radius: 6px;
      background: rgba(15, 26, 46, 0.8); color: #dce6f1;
      font-size: 10px; padding: 4px 8px; cursor: pointer;
    }}
    .window-clear-btn:disabled {{ opacity: 0.4; cursor: default; }}
    .year-nav {{
      position: absolute; right: 10px; top: 6px; display: none; align-items: center; gap: 6px;
      font-size: 11px; color: #c4d1e0;
    }}
    .year-nav button {{
      border: 1px solid #33465f; background: #0c1628; color: #d7e3f1; border-radius: 6px;
      width: 22px; height: 20px; line-height: 18px; padding: 0; cursor: pointer;
    }}
    .year-nav button:disabled {{ opacity: 0.35; cursor: default; }}
    .year-nav .year-label {{ min-width: 44px; text-align: center; font-weight: 600; }}
    .timeline {{ position: absolute; left: 8px; right: 8px; top: 4px; height: 56px; pointer-events: auto; overflow: hidden; }}
    .timeline-slider-spikes {{
      position: absolute; left: 8px; right: 8px; bottom: 0px; height: 24px;
      pointer-events: none;
    }}
    .timeline-slider {{
      position: absolute; left: 20px; right: 20px; bottom: 18px; height: 20px;
      appearance: none;
      -webkit-appearance: none;
      background: transparent;
    }}
    .t-brush .selection {{
      fill: rgba(255, 255, 255, 0.14);
      stroke: #d7e3f1;
      stroke-width: 1px;
    }}
    .t-brush .handle {{
      fill: rgba(215, 227, 241, 0.8);
      stroke: none;
      width: 4px;
    }}
    .t-brush .overlay {{ cursor: crosshair; }}
    .timeline-slider:focus {{
      outline: none;
    }}
    .timeline-slider::-webkit-slider-runnable-track {{
      height: 8px;
      border-radius: 999px;
      background: #697587;
      border: 1px solid #99a3b2;
    }}
    .timeline-slider::-webkit-slider-thumb {{
      -webkit-appearance: none;
      width: 16px;
      height: 16px;
      margin-top: -5px;
      border-radius: 50%;
      background: #d6dee8;
      border: 2px solid #8a97aa;
      box-shadow: 0 0 0 2px rgba(6, 13, 26, 0.9);
      cursor: pointer;
    }}
    .timeline-slider::-moz-range-track {{
      height: 8px;
      border-radius: 999px;
      background: #697587;
      border: 1px solid #99a3b2;
    }}
    .timeline-slider::-moz-range-progress {{
      height: 8px;
      border-radius: 999px;
      background: #697587;
      border: 1px solid #99a3b2;
    }}
    .timeline-slider::-moz-range-thumb {{
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: #d6dee8;
      border: 2px solid #8a97aa;
      box-shadow: 0 0 0 2px rgba(6, 13, 26, 0.9);
      cursor: pointer;
    }}
    svg.graph-svg {{ width: 100%; height: 100%; background: #ffffff; }}
    .t-spike {{ stroke: #aab3bc; stroke-width: 2px; opacity: 0.65; }}
    .t-add {{ fill: #2ecc71; }}
    .t-del {{ fill: #e74c3c; }}
    .t-border {{ fill: none; stroke: #9aa4ad; stroke-width: 1px; }}
    .t-click {{ fill: transparent; cursor: pointer; }}
    .t-current {{ stroke: #fff; stroke-width: 2px; fill: none; }}

    .link {{ stroke-width: 2px; opacity: 0.95; }}
    .edge-label {{ font-size: 8px; fill: #2f3a46; opacity: 0.95; pointer-events: none; }}
    .edge-label-bg {{ stroke: rgba(255,255,255,0.95); stroke-width: 2px; paint-order: stroke; stroke-linejoin: round; }}
    .node circle {{ stroke: #fff; stroke-width: 1.5px; }}
    .label {{
      font-size: 6.6px; font-weight: 600; fill: #0f1720; text-anchor: middle;
      dominant-baseline: middle; pointer-events: none;
    }}

    .source-toggle {{
      position: absolute; right: 12px; top: 10px; z-index: 12;
      border: 1px solid #cfcfcf; background: #fff; border-radius: 8px;
      padding: 6px 10px; font-size: 12px; cursor: pointer;
    }}

    .tooltip {{
      position: absolute; padding: 8px 10px; background: rgba(0,0,0,0.75);
      color: white; border-radius: 8px; font-size: 12px; pointer-events: none;
      transform: translate(-50%, -120%); display: none; white-space: nowrap;
      z-index: 20;
    }}

    .legend {{
      position: absolute; left: 10px; top: 10px; background: rgba(255,255,255,0.95);
      border: 1px solid #ddd; border-radius: 10px; padding: 8px 10px; font-size: 12px; z-index: 11;
    }}
    .legend-row {{ display:flex; gap:8px; align-items:center; margin: 4px 0; }}
    .swatch {{ width: 14px; height: 14px; border-radius: 3px; display:inline-block; }}

    .src-head {{ padding: 10px 12px; border-bottom: 1px solid #ddd; background: #fff; }}
    .src-title {{ font-size: 13px; font-weight: 700; margin-bottom: 8px; }}
    .src-tabs {{ display: flex; gap: 6px; flex-wrap: wrap; }}
    .src-tab {{
      border: 1px solid #d2d2d2; background: #fff; border-radius: 16px;
      padding: 4px 10px; font-size: 12px; cursor: pointer;
    }}
    .src-tab.active {{ background: #222; color: #fff; border-color: #222; }}
    .src-tab.has-hover-match {{ border-color: #ff8f2a; box-shadow: 0 0 0 1px rgba(255,143,42,0.55) inset; }}

    .src-meta {{ padding: 8px 12px; font-size: 12px; background: #fff; border-bottom: 1px solid #e1e1e1; }}
    .src-body {{
      flex: 1 1 auto; overflow: auto; padding: 12px;
      font-size: 13px; line-height: 1.45; white-space: pre-wrap; word-break: break-word;
      text-align: justify; text-justify: inter-word;
      box-sizing: border-box; padding-bottom: 36px;
      min-height: 0;
      background: #fff;
    }}
    .ep-chunk {{ border-radius: 2px; }}
    .ep-chunk:hover {{ background: #e8f2ff; }}
    .hl {{ background: #fff3a6; border-radius: 2px; }}
    .src-bottom-spacer {{ display: block; width: 100%; height: 52px; }}
    .hint {{ color: #666; font-size: 12px; }}
  </style>
</head>
<body>
<div class="wrap" id="wrap">
  <div class="timeline-shell" id="timelineShell">
    <svg class="timeline" id="timeline"></svg>
    <svg class="timeline-slider-spikes" id="timelineSliderSpikes"></svg>
    <input class="timeline-slider" id="timelineSlider" type="range" min="0" max="0" value="0" step="1"/>
    <div class="window-summary" id="windowSummary">
      <div class="window-summary-text" id="windowSummaryText">Drag over the bars to pick a custom window, then click Clear to return to single steps.</div>
      <button class="window-clear-btn" id="windowClear" disabled>Clear window</button>
    </div>
    <div class="year-nav" id="yearNav">
      <button id="yearPrev" title="Previous year">◀</button>
      <span class="year-label" id="yearLabel">-</span>
      <button id="yearNext" title="Next year">▶</button>
    </div>
  </div>
  <div class="layout" id="layout">
    <div class="graph-pane" id="graphPane">
      <button class="source-toggle" id="sourceToggle">See source</button>
      <div class="legend">
        <div><b>Legend</b></div>
        <div class="legend-row"><span class="swatch" style="background:#2ecc71;"></span> new (this timestep)</div>
        <div class="legend-row"><span class="swatch" style="background:#95a5a6;"></span> active (existing)</div>
        <div class="legend-row"><span class="swatch" style="background:#e74c3c;"></span> invalid (retracted now)</div>
      </div>
      <div class="tooltip" id="tt"></div>
      <svg class="graph-svg" id="svg"></svg>
    </div>

    <aside class="source-pane hidden" id="sourcePane">
      <div class="src-head">
        <div class="src-title">Source documents in this timestep</div>
        <div class="src-tabs" id="srcTabs"></div>
      </div>
      <div class="src-meta" id="srcMeta"></div>
      <div class="src-body" id="srcBody"></div>
    </aside>
  </div>
</div>

<script>
const payload = {data_json};
const sources = payload.sources || {{}};
const episodes = payload.episodes || {{}};
const frames = payload.frames || [];
const timestepLabels = payload.labels || [];
const payloadGranularity = String(payload.granularity || "").toLowerCase();
let currentIdx = Math.max(0, Math.min({frame_idx}, Math.max(0, frames.length - 1)));

const wrapEl = document.getElementById("wrap");
const W = Math.max(640, wrapEl.clientWidth || {width});
const H = Math.max(420, wrapEl.clientHeight || {height});
const TL_H = 94;
const GH = H - TL_H;
const svg = d3.select("#svg").attr("viewBox", [0,0,W,GH]);
svg.selectAll("*").remove();
const timelineSvg = d3.select("#timeline").attr("viewBox", [0,0,W,TL_H]);
const timelineSliderSpikesSvg = d3.select("#timelineSliderSpikes").attr("viewBox", [0,0,W,24]);

const tooltip = d3.select("#tt");
const sourcePane = document.getElementById("sourcePane");
const sourceToggle = document.getElementById("sourceToggle");
const srcTabs = document.getElementById("srcTabs");
const srcMeta = document.getElementById("srcMeta");
const srcBody = document.getElementById("srcBody");
const timelineSlider = document.getElementById("timelineSlider");
const timelineShell = document.getElementById("timelineShell");
const yearNav = document.getElementById("yearNav");
const yearPrev = document.getElementById("yearPrev");
const yearNext = document.getElementById("yearNext");
const yearLabel = document.getElementById("yearLabel");
const windowSummary = document.getElementById("windowSummary");
const windowSummaryText = document.getElementById("windowSummaryText");
const windowClearBtn = document.getElementById("windowClear");

let activeDoc = null;
let activeHighlightEpisodeUuids = [];
let sourceOpen = false;
let nodeSelection = null;
let edgeGroupSelection = null;
let edgePathSelection = null;
let nodeIdsByEpisode = new Map();
let edgeKeysByEpisode = new Map();
let graphEpisodeHoverActive = false;
let customWindow = null;
let customWindowFrameCache = null;
let suppressBrushSync = false;
const monthNames = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"];
const isMonthGranularity =
  payloadGranularity === "month" ||
  (timestepLabels.length > 0 && timestepLabels.every(l => /^\\d{4}-\\d{2}$/.test(String(l))));
const monthMeta = isMonthGranularity
  ? timestepLabels.map((l, i) => {{
      const [y, m] = String(l).split("-");
      return {{ frameIdx: i, year: Number(y), month: Number(m) }};
    }})
  : [];
const availableYears = isMonthGranularity ? Array.from(new Set(monthMeta.map(m => m.year))).sort((a, b) => a - b) : [];
let activeYear = isMonthGranularity
  ? (monthMeta[currentIdx] ? monthMeta[currentIdx].year : availableYears[0])
  : null;

function colorForStatus(status) {{
  if (status === "new") return "#2ecc71";
  if (status === "invalid") return "#e74c3c";
  if (status === "new_invalid") return "#2ecc71";
  return "#95a5a6";
}}

function invalidOpacity(age) {{
  if (age === null || age === undefined) return 1;
  return Math.max(0.18, 1 - (Number(age) * 0.14));
}}

function seededRandom(seed) {{
  let s = seed >>> 0;
  return function() {{
    s = (1664525 * s + 1013904223) >>> 0;
    return s / 4294967296;
  }};
}}

function hashId(str) {{
  let h = 2166136261;
  const s = String(str);
  for (let i = 0; i < s.length; i += 1) {{
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }}
  return h >>> 0;
}}

function escapeHtml(text) {{
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}}

function frameAt(i) {{
  return frames[i] || {{ nodes: [], links: [], doc_names: [] }};
}}

function collectDocContexts(docName, episodeUuids) {{
  const snippets = [];
  for (const epUuid of (episodeUuids || [])) {{
    const ep = episodes[epUuid];
    if (!ep || ep.source_text_name !== docName) continue;
    let ctx = String(ep.context || "").trim();
    ctx = ctx.replace(/^\s*\[section:[^\]]*\]\s*/i, "");
    if (!ctx) continue;
    snippets.push(ctx);
  }}
  return snippets;
}}

function canonicalizeWithMap(text) {{
  const raw = String(text || "");
  let out = "";
  const map = [];
  let i = 0;
  while (i < raw.length) {{
    if (raw[i] === "[") {{
      let j = i + 1;
      while (j < raw.length && /\d/.test(raw[j])) j += 1;
      if (j > i + 1 && j < raw.length && raw[j] === "]") {{ i = j + 1; continue; }}
    }}
    const ch = raw[i];
    if (/\s/.test(ch)) {{
      let j = i + 1;
      while (j < raw.length && /\s/.test(raw[j])) j += 1;
      if (out.length > 0 && !out.endsWith(" ")) {{ out += " "; map.push(i); }}
      i = j;
      continue;
    }}
    out += ch.toLowerCase();
    map.push(i);
    i += 1;
  }}
  if (out.endsWith(" ")) {{ out = out.slice(0, -1); map.pop(); }}
  return {{ text: out, map }};
}}

function findAllRangesFromCanonical(docText, snippets) {{
  const canonDoc = canonicalizeWithMap(docText);
  const docNorm = canonDoc.text;
  const normToRaw = canonDoc.map;
  const ranges = [];

  for (const snippet of (snippets || [])) {{
    const sNorm = canonicalizeWithMap(snippet).text;
    if (!sNorm || sNorm.length < 20) continue;
    let from = 0;
    while (true) {{
      const at = docNorm.indexOf(sNorm, from);
      if (at === -1) break;
      const endNorm = at + sNorm.length - 1;
      const rawStart = normToRaw[at];
      const rawEnd = (normToRaw[endNorm] ?? rawStart) + 1;
      if (rawStart !== undefined && rawEnd !== undefined && rawEnd > rawStart) ranges.push([rawStart, rawEnd]);
      from = at + 1;
    }}
  }}

  if (!ranges.length) return ranges;
  ranges.sort((a, b) => a[0] - b[0]);
  const merged = [ranges[0]];
  for (let i = 1; i < ranges.length; i += 1) {{
    const cur = ranges[i];
    const prev = merged[merged.length - 1];
    if (cur[0] <= prev[1]) prev[1] = Math.max(prev[1], cur[1]);
    else merged.push(cur);
  }}
  return merged;
}}

function renderWithHighlights(rawText, ranges) {{
  if (!ranges || !ranges.length) return escapeHtml(rawText || "");
  let out = "";
  let pos = 0;
  for (const [start, end] of ranges) {{
    if (start > pos) out += escapeHtml(rawText.slice(pos, start));
    out += `<span class="hl">${{escapeHtml(rawText.slice(start, end))}}</span>`;
    pos = end;
  }}
  if (pos < rawText.length) out += escapeHtml(rawText.slice(pos));
  return out;
}}

function visibleTimelineItems() {{
  if (!isMonthGranularity) {{
    return frames.map((_, i) => ({{
      slot: i,
      frameIdx: i,
      tickLabel: timestepLabels[i] ?? String(i),
    }}));
  }}

  const byMonth = new Map();
  for (const m of monthMeta) {{
    if (m.year === activeYear) byMonth.set(m.month, m.frameIdx);
  }}
  const out = [];
  for (let m = 1; m <= 12; m += 1) {{
    out.push({{
      slot: m - 1,
      frameIdx: byMonth.has(m) ? byMonth.get(m) : null,
      tickLabel: monthNames[m - 1],
    }});
  }}
  return out;
}}

function frameMods(frameIdx) {{
  if (frameIdx === null || frameIdx === undefined) return {{ add: 0, del: 0, total: 0 }};
  const f = frameAt(frameIdx);
  const add = (f.nodes || []).filter(x => x.is_new).length +
    (f.links || []).filter(x => x.is_new).length;
  const del = (f.nodes || []).filter(x => x.is_invalid).length +
    (f.links || []).filter(x => x.is_invalid).length;
  return {{ add, del, total: add + del }};
}}

function labelForFrameIdx(idx) {
  if (idx === null || idx === undefined) return "-";
  const label = timestepLabels[idx];
  if (label !== undefined) return String(label);
  return `Frame ${idx + 1}`;
}

function composeWindowFrame(startIdx, endIdx) {
  if (!frames.length) return { nodes: [], links: [], doc_names: [] };
  const start = Math.max(0, Math.min(startIdx, frames.length - 1));
  const end = Math.max(start, Math.min(endIdx, frames.length - 1));
  const nodeMap = new Map();
  const linkMap = new Map();
  const docNames = new Set();

  for (let i = start; i <= end; i += 1) {
    const frame = frameAt(i);
    if (!frame) continue;
    (frame.doc_names || []).forEach(name => docNames.add(String(name)));

    (frame.nodes || []).forEach(n => {
      const key = String(n.id);
      const entry = nodeMap.get(key) || {
        id: n.id,
        label: n.label,
        added: false,
        invalidated: false,
        episodes: new Set(),
      };
      entry.added = entry.added || Boolean(n.is_new);
      entry.invalidated = entry.invalidated || Boolean(n.is_invalid);
      (n.episode_uuids || []).forEach(ep => entry.episodes.add(String(ep)));
      nodeMap.set(key, entry);
    });

    (frame.links || []).forEach(l => {
      const key = String(l.id);
      const entry = linkMap.get(key) || {
        id: l.id,
        label: l.label,
        source: l.source,
        target: l.target,
        added: false,
        invalidated: false,
        episodes: new Set(),
      };
      entry.added = entry.added || Boolean(l.is_new);
      entry.invalidated = entry.invalidated || Boolean(l.is_invalid);
      (l.episode_uuids || []).forEach(ep => entry.episodes.add(String(ep)));
      linkMap.set(key, entry);
    });
  }

  const nodes = [];
  nodeMap.forEach(entry => {
    if (!entry.added && !entry.invalidated) return;
    let status = "active";
    if (entry.added && entry.invalidated) status = "new_invalid";
    else if (entry.added) status = "new";
    else if (entry.invalidated) status = "invalid";
    nodes.push({
      id: entry.id,
      label: entry.label,
      status,
      is_new: entry.added,
      is_invalid: entry.invalidated,
      invalid_age: entry.invalidated ? 0 : null,
      episode_uuids: Array.from(entry.episodes).sort(),
    });
  });
  nodes.sort((a, b) => String(a.label || a.id).localeCompare(String(b.label || b.id)));

  const links = [];
  linkMap.forEach(entry => {
    if (!entry.added && !entry.invalidated) return;
    let status = "active";
    if (entry.added && entry.invalidated) status = "new_invalid";
    else if (entry.added) status = "new";
    else if (entry.invalidated) status = "invalid";
    links.push({
      id: entry.id,
      source: entry.source,
      target: entry.target,
      label: entry.label,
      status,
      is_new: entry.added,
      is_invalid: entry.invalidated,
      invalid_age: entry.invalidated ? 0 : null,
      episode_uuids: Array.from(entry.episodes).sort(),
    });
  });
  links.sort((a, b) => String(a.label || a.id).localeCompare(String(b.label || b.id)));

  const orderedDocNames = Array.from(docNames).sort((a, b) => {
    const aMeta = sources[a] || {};
    const bMeta = sources[b] || {};
    const dateCmp = String(aMeta.date_accessed || "9999-12-31").localeCompare(String(bMeta.date_accessed || "9999-12-31"));
    if (dateCmp !== 0) return dateCmp;
    return String(a).localeCompare(String(b));
  });

  return { nodes, links, doc_names: orderedDocNames };
}

function currentFramePayload() {
  if (customWindowFrameCache) return customWindowFrameCache;
  return frameAt(currentIdx);
}

function updateWindowSummary() {
  if (!windowSummary || !windowSummaryText || !windowClearBtn) return;
  if (!customWindow) {
    windowSummary.classList.remove("active");
    windowSummaryText.innerHTML = "Drag over the bars to pick a custom window, then click Clear to return to single steps.";
    windowClearBtn.disabled = true;
    timelineSlider.disabled = false;
    return;
  }
  windowSummary.classList.add("active");
  const startLabel = labelForFrameIdx(customWindow.startIdx);
  const endLabel = labelForFrameIdx(customWindow.endIdx);
  const priorLabel = customWindow.startIdx > 0 ? labelForFrameIdx(customWindow.startIdx - 1) : "timeline start";
  const span = customWindow.endIdx - customWindow.startIdx + 1;
  const nodesInWindow = (customWindowFrameCache && Array.isArray(customWindowFrameCache.nodes)) ? customWindowFrameCache.nodes.length : 0;
  const linksInWindow = (customWindowFrameCache && Array.isArray(customWindowFrameCache.links)) ? customWindowFrameCache.links.length : 0;
  const changeCount = nodesInWindow + linksInWindow;
  const changeLabel = changeCount ? `${changeCount} change${changeCount === 1 ? "" : "s"}` : "no changes";
  windowSummaryText.innerHTML = `Window <b>${startLabel}</b> → <b>${endLabel}</b> (${span} steps, ${changeLabel}). Showing changes since ${priorLabel}.`;
  windowClearBtn.disabled = false;
  timelineSlider.disabled = true;
}

function setCustomWindow(startIdx, endIdx) {
  const start = Math.max(0, Math.min(startIdx, frames.length - 1));
  const end = Math.max(start, Math.min(endIdx, frames.length - 1));
  customWindow = { startIdx: start, endIdx: end };
  customWindowFrameCache = composeWindowFrame(start, end);
  updateWindowSummary();
  renderTimeline();
  renderSliderSpikes();
  renderGraph();
  renderTabs();
}

function clearCustomWindow(shouldRender = true) {
  customWindow = null;
  customWindowFrameCache = null;
  updateWindowSummary();
  if (shouldRender) {
    renderTimeline();
    renderSliderSpikes();
    renderGraph();
    renderTabs();
  }
}

function slotForFrameIdx(idx, visibleItems) {
  const item = visibleItems.find(v => v.frameIdx === idx);
  return item ? item.slot : null;
}

function updateYearNav() {{
  if (!isMonthGranularity) {{
    yearNav.style.display = "none";
    return;
  }}
  yearNav.style.display = "flex";
  yearLabel.textContent = String(activeYear ?? "");
  const idx = availableYears.indexOf(activeYear);
  yearPrev.disabled = idx <= 0;
  yearNext.disabled = idx >= availableYears.length - 1;
}}

function docsForActiveEpisodeHover() {
  const docs = currentFramePayload().doc_names || [];
  if (!activeHighlightEpisodeUuids.length) return [];
  const docSet = new Set();
  for (const epUuid of activeHighlightEpisodeUuids) {{
    const ep = episodes[epUuid];
    if (!ep || !ep.source_text_name) continue;
    if (docs.includes(ep.source_text_name)) docSet.add(ep.source_text_name);
  }}
  // preserve chronological order (frame.doc_names already sorted by date)
  return docs.filter(d => docSet.has(d));
}}

function scrollToFirstHighlight() {{
  const first = srcBody.querySelector(".ep-chunk.hl");
  if (first) {{
    const targetTop = first.offsetTop - (srcBody.clientHeight * 0.35);
    const nextTop = Math.max(0, targetTop);
    srcBody.scrollTo({{ top: nextTop, behavior: "smooth" }});
  }}
}}

function renderTabs() {
  srcTabs.innerHTML = "";
  const docs = currentFramePayload().doc_names || [];
  const hoverDocs = new Set(docsForActiveEpisodeHover());

  if (!docs.length) {{
    srcMeta.innerHTML = '<span class="hint">No source documents for this timestep.</span>';
    srcBody.innerHTML = '<span class="hint">No text to display.</span>';
    return;
  }}

  if (!activeDoc || !docs.includes(activeDoc)) activeDoc = docs[0];
  for (const docName of docs) {{
    const btn = document.createElement("button");
    btn.className = "src-tab" + (docName === activeDoc ? " active" : "") + (hoverDocs.has(docName) ? " has-hover-match" : "");
    btn.textContent = docName;
    btn.onclick = () => {{ activeDoc = docName; renderTabs(); renderDocBody(); }};
    srcTabs.appendChild(btn);
  }}
  renderDocBody();
}}

function renderDocBody() {{
  const docName = activeDoc;
  const doc = sources[docName];
  if (!doc) {{
    srcMeta.innerHTML = '<span class="hint">Missing source metadata.</span>';
    srcBody.innerHTML = '<span class="hint">Missing source text.</span>';
    return;
  }}

  const dateText = doc.date_accessed ? `Date: <b>${{escapeHtml(doc.date_accessed)}}</b>` : "Date: -";
  const linkText = doc.link ? `Source: <a href="${{escapeHtml(doc.link)}}" target="_blank" rel="noopener noreferrer">${{escapeHtml(doc.link)}}</a>` : "Source: -";
  srcMeta.innerHTML = `${{dateText}}<br/>${{linkText}}`;

  const rawDoc = String(doc.text || "");
  const frame = currentFramePayload();
  const epSet = new Set();
  for (const n of (frame.nodes || [])) for (const e of (n.episode_uuids || [])) epSet.add(String(e));
  for (const l of (frame.links || [])) for (const e of (l.episode_uuids || [])) epSet.add(String(e));

  const intervals = [];
  for (const epUuid of epSet) {{
    const ep = episodes[epUuid];
    if (!ep || ep.source_text_name !== docName) continue;
    const txt = String(ep.context || "").replace(/^\\s*\\[section:[^\\]]*\\]\\s*/i, "").trim();
    if (!txt) continue;
    const ranges = findAllRangesFromCanonical(rawDoc, [txt]);
    for (const [start, end] of ranges) {{
      intervals.push({{ start, end, epUuid }});
    }}
  }}

  intervals.sort((a, b) => (a.start - b.start) || (b.end - a.end));
  let html = "";
  let pos = 0;
  for (const r of intervals) {{
    if (r.start < pos || r.end <= r.start) continue;
    if (r.start > pos) html += escapeHtml(rawDoc.slice(pos, r.start));
    const snippet = escapeHtml(rawDoc.slice(r.start, r.end));
    const cls = activeHighlightEpisodeUuids.includes(r.epUuid) ? "ep-chunk hl" : "ep-chunk";
    html += `<span class="${{cls}}" data-ep-uuids="${{escapeHtml(r.epUuid)}}">${{snippet}}</span>`;
    pos = r.end;
  }}
  if (pos < rawDoc.length) html += escapeHtml(rawDoc.slice(pos));
  srcBody.innerHTML = (html || '<span class="hint">Empty source text.</span>') + '<div class="src-bottom-spacer"></div>';

  srcBody.querySelectorAll(".ep-chunk").forEach(el => {{
    const ep = el.getAttribute("data-ep-uuids");
    el.addEventListener("mouseenter", () => applyGraphEpisodeHover(ep ? [ep] : []));
    el.addEventListener("mouseleave", () => resetGraphEpisodeHover());
  }});
}}

function setSourceOpen(open) {{
  sourceOpen = open;
  sourcePane.classList.toggle("hidden", !open);
  sourceToggle.textContent = open ? "Hide source" : "See source";
}}
sourceToggle.onclick = () => setSourceOpen(!sourceOpen);

function setHighlightForEpisodeUuids(epUuids) {{
  activeHighlightEpisodeUuids = Array.from(new Set(epUuids || []));
  if (!sourceOpen) return;

  const matchingDocs = docsForActiveEpisodeHover();
  if (matchingDocs.length) {{
    // If current doc has no highlight, switch to earliest matching doc.
    if (!matchingDocs.includes(activeDoc)) activeDoc = matchingDocs[0];
  }}
  renderTabs();
  // After render, jump user to first visible highlighted chunk in active doc.
  if (activeHighlightEpisodeUuids.length) {{
    setTimeout(() => scrollToFirstHighlight(), 0);
  }}
}}

function resetGraphEpisodeHover() {{
  graphEpisodeHoverActive = false;
  if (nodeSelection) nodeSelection.style("filter", null);
  if (edgeGroupSelection) edgeGroupSelection.style("filter", null);
}}

function applyGraphEpisodeHover(epUuids) {{
  const ids = Array.from(new Set(epUuids || []));
  if (!ids.length || !nodeSelection || !edgeGroupSelection) {{
    resetGraphEpisodeHover();
    return;
  }}

  const nodeIds = new Set();
  const edgeKeys = new Set();
  for (const ep of ids) {{
    const nset = nodeIdsByEpisode.get(ep);
    const eset = edgeKeysByEpisode.get(ep);
    if (nset) for (const nid of nset) nodeIds.add(nid);
    if (eset) for (const ek of eset) edgeKeys.add(ek);
  }}

  if (!nodeIds.size && !edgeKeys.size) {{
    resetGraphEpisodeHover();
    return;
  }}

  graphEpisodeHoverActive = true;
  nodeSelection.style("filter", d => (nodeIds.has(String(d.id))
    ? "drop-shadow(0 0 8px rgba(34,269,227,0.998))"
    : null));
  edgeGroupSelection.style("filter", d => (edgeKeys.has(`${{d.id}}-${{d.parallel_index}}`)
    ? "drop-shadow(0 0 7px rgba(34,269,227,0.998))"
    : null));
}}

// -------- Global static layout (all nodes/links across all frames) --------
const nodeMap = new Map();
const linkMap = new Map();
for (const f of frames) {{
  for (const n of (f.nodes || [])) if (!nodeMap.has(n.id)) nodeMap.set(n.id, {{ id: n.id, label: n.label }});
  for (const l of (f.links || [])) if (!linkMap.has(l.id)) linkMap.set(l.id, {{ id: l.id, source: l.source, target: l.target }});
}}
const allNodes = Array.from(nodeMap.values());
const allLinks = Array.from(linkMap.values());

for (const n of allNodes) {{
  const rnd = seededRandom(hashId(n.id));
  n.x = (rnd() - 0.5) * (W * 0.7) + (W / 2);
  n.y = (rnd() - 0.5) * (GH * 0.7) + (GH / 2);
}}

const layoutSim = d3.forceSimulation(allNodes)
  .randomSource(seededRandom(42))
  .force("link", d3.forceLink(allLinks).id(d => d.id).distance(120).strength(0.55))
  .force("charge", d3.forceManyBody().strength(-420))
  .force("center", d3.forceCenter(W / 2, GH / 2))
  .force("collide", d3.forceCollide(40))
  .stop();
for (let i = 0; i < 350; i += 1) layoutSim.tick();

const posById = new Map(allNodes.map(n => [n.id, {{ x: n.x, y: n.y }}]));
const NODE_R = 24;

const defs = svg.append("defs");
defs.append("marker")
  .attr("id","arrow")
  .attr("viewBox","0 -5 10 10")
  .attr("refX", 8)
  .attr("refY", 0)
  .attr("markerWidth", 6)
  .attr("markerHeight", 6)
  .attr("orient","auto")
  .append("path")
  .attr("d","M0,-5L10,0L0,5")
  .attr("fill","#999");

const g = svg.append("g");
svg.call(d3.zoom().scaleExtent([0.2, 3]).on("zoom", (event) => g.attr("transform", event.transform)));

function makeRenderData(frame) {{
  const renderNodes = (frame.nodes || []).map(n => {{
    const p = posById.get(n.id) || {{ x: W / 2, y: GH / 2 }};
    return {{ ...n, x: p.x, y: p.y }};
  }});

  const renderLinks = (frame.links || []).map(l => ({{ ...l }}));
  const pairBuckets = new Map();
  for (const l of renderLinks) {{
    const a = String(l.source), b = String(l.target);
    const key = a < b ? `${{a}}||${{b}}` : `${{b}}||${{a}}`;
    if (!pairBuckets.has(key)) pairBuckets.set(key, []);
    pairBuckets.get(key).push(l);
  }}
  for (const group of pairBuckets.values()) {{
    const total = group.length;
    group.forEach((l, idx) => {{
      l.parallel_total = total;
      l.parallel_index = idx;
      l.path_id = `edge-path-${{String(l.id).replace(/[^A-Za-z0-9_-]/g, "_")}}-${{idx}}`;
    }});
  }}
  return {{ renderNodes, renderLinks }};
}}

function edgeGeometry(l, nodePos, normalExtra = 0, reverse = false) {{
  const s = nodePos.get(l.source) || {{ x: W / 2, y: GH / 2 }};
  const t = nodePos.get(l.target) || {{ x: W / 2, y: GH / 2 }};
  let sx = s.x, sy = s.y, tx = t.x, ty = t.y;

  if (l.source === l.target) {{
    const loopR = NODE_R + 8 + (l.parallel_index || 0) * 10;
    const x1 = sx, y1 = sy - 14;
    const cx1 = sx + loopR, cy1 = sy - loopR;
    const cx2 = sx - loopR, cy2 = sy - loopR;
    const x2 = sx + 1, y2 = sy - 14;
    return {{ sx: x1, sy: y1, tx: x2, ty: y2, cx: cx1, cy: cy1, path: `M ${{x1}} ${{y1}} C ${{cx1}} ${{cy1}}, ${{cx2}} ${{cy2}}, ${{x2}} ${{y2}}` }};
  }}

  if (reverse) {{
    const ax = sx, ay = sy;
    sx = tx; sy = ty;
    tx = ax; ty = ay;
  }}

  const dx = tx - sx, dy = ty - sy;
  const len = Math.max(1, Math.hypot(dx, dy));
  const nx = -dy / len, ny = dx / len;
  const total = l.parallel_total || 1;
  const idx = l.parallel_index || 0;
  const parallelOffset = total > 1 ? (idx - (total - 1) / 2) * 18 : 0;
  const labelOffset = normalExtra;
  const offset = parallelOffset + labelOffset;

  // trim line ends to node boundary so arrows are visible
  const trim = NODE_R + 2;
  const ssx = sx + (dx / len) * trim;
  const ssy = sy + (dy / len) * trim;
  const ttx = tx - (dx / len) * trim;
  const tty = ty - (dy / len) * trim;

  const cx = (ssx + ttx) / 2 + nx * offset;
  const cy = (ssy + tty) / 2 + ny * offset;
  return {{ sx: ssx, sy: ssy, tx: ttx, ty: tty, cx, cy, path: `M ${{ssx}} ${{ssy}} Q ${{cx}} ${{cy}} ${{ttx}} ${{tty}}` }};
}}

function shouldReverseLabel(l, nodePos) {{
  const s = nodePos.get(l.source) || {{ x: W / 2, y: GH / 2 }};
  const t = nodePos.get(l.target) || {{ x: W / 2, y: GH / 2 }};
  const angle = Math.atan2(t.y - s.y, t.x - s.x) * 180 / Math.PI;
  return angle > 90 || angle < -90;
}}

function linkPathD(l, nodePos) {{
  return edgeGeometry(l, nodePos, 0, false).path;
}}

function labelPathD(l, nodePos) {{
  const reverse = shouldReverseLabel(l, nodePos);
  // place label a bit above path
  return edgeGeometry(l, nodePos, -8, reverse).path;
}}

function edgeLabelPos(l, nodePos) {{
  const s = nodePos.get(l.source) || {{ x: W / 2, y: GH / 2 }};
  const t = nodePos.get(l.target) || {{ x: W / 2, y: GH / 2 }};
  const sx = s.x, sy = s.y, tx = t.x, ty = t.y;
  const dx = tx - sx, dy = ty - sy;
  const len = Math.max(1, Math.hypot(dx, dy));
  const nx = -dy / len, ny = dx / len;
  const total = l.parallel_total || 1;
  const idx = l.parallel_index || 0;
  const offset = total > 1 ? (idx - (total - 1) / 2) * 18 : 0;
  const cx = (sx + tx) / 2 + nx * offset;
  const cy = (sy + ty) / 2 + ny * offset;
  // keep text off the path for readability
  return {{ x: cx + nx * 10, y: cy + ny * 10 }};
}}

function fitNodeLabel(text, maxChars = 16) {{
  const t = String(text || "").trim();
  if (t.length <= maxChars) return t;
  return t.slice(0, Math.max(3, maxChars - 1)) + "…";
}}

function nodeLabelLines(text, maxChars = 16) {{
  const clipped = fitNodeLabel(text, maxChars);
  if (clipped.length <= 8) return [clipped];

  const words = clipped.split(/\\s+/).filter(Boolean);
  if (words.length <= 1) {{
    const mid = Math.ceil(clipped.length / 2);
    return [clipped.slice(0, mid), clipped.slice(mid)];
  }}

  let best = [clipped, ""];
  let left = words[0];
  for (let i = 1; i < words.length; i += 1) {{
    const right = words.slice(i).join(" ");
    const delta = Math.abs(left.length - right.length);
    const bestDelta = Math.abs(best[0].length - best[1].length);
    if (delta < bestDelta) best = [left, right];
    left += " " + words[i];
  }}
  if (!best[1]) return [best[0]];
  return [best[0], best[1]];
}}

function renderGraph() {{
  const frame = currentFramePayload();
  const {{ renderNodes, renderLinks }} = makeRenderData(frame);
  const nodePos = new Map(renderNodes.map(n => [n.id, {{ x: n.x, y: n.y }}]));

  g.selectAll("*").remove();

  const edgeGroup = g.append("g").selectAll("g.edge")
    .data(renderLinks, d => `${{d.id}}-${{d.parallel_index}}`)
    .join("g")
    .attr("class", "edge")
    .style("opacity", d => ((d.status === "invalid" || d.status === "new_invalid")
      ? invalidOpacity(d.invalid_age)
      : 1));

  const link = edgeGroup.append("path")
    .attr("id", d => d.path_id)
    .attr("class", "link")
    .attr("stroke", d => colorForStatus(d.status))
    .attr("fill", "none")
    .attr("d", d => linkPathD(d, nodePos))
    .attr("marker-end", "url(#arrow)");

  // For edges that are both added and retracted in this timestep,
  // overlay red on the second half of the same path.
  edgeGroup
    .filter(d => d.status === "new_invalid")
    .append("path")
    .attr("class", "link")
    .attr("stroke", "#e74c3c")
    .attr("fill", "none")
    .attr("d", d => linkPathD(d, nodePos))
    .attr("pathLength", 100)
    .attr("stroke-dasharray", "50 50")
    .attr("stroke-dashoffset", -50)
    .attr("marker-end", "url(#arrow)");

  edgeGroup.append("path")
    .attr("id", d => `${{d.path_id}}-label`)
    .attr("d", d => labelPathD(d, nodePos))
    .attr("fill", "none")
    .attr("stroke", "none");

  edgeGroup.append("text")
    .attr("class", "edge-label edge-label-bg")
    .append("textPath")
    .attr("href", d => `#${{d.path_id}}-label`)
    .attr("startOffset", "50%")
    .attr("text-anchor", "middle")
    .text(d => String(d.label || "").toLowerCase());

  edgeGroup.append("text")
    .attr("class", "edge-label")
    .append("textPath")
    .attr("href", d => `#${{d.path_id}}-label`)
    .attr("startOffset", "50%")
    .attr("text-anchor", "middle")
    .text(d => String(d.label || "").toLowerCase());

  const node = g.append("g")
    .selectAll("g")
    .data(renderNodes, d => d.id)
    .join("g")
    .attr("class", "node")
    .attr("transform", d => `translate(${{d.x}},${{d.y}})`)
    .style("opacity", d => ((d.status === "invalid" || d.status === "new_invalid")
      ? invalidOpacity(d.invalid_age)
      : 1))
    .call(d3.drag().on("drag", dragged));

  node.append("circle")
    .attr("r", NODE_R)
    .attr("fill", d => (d.status === "new_invalid" ? "none" : colorForStatus(d.status)));

  // Draw symmetric half-disks for combined new+invalid state.
  const splitNodes = node.filter(d => d.status === "new_invalid");
  splitNodes.append("path")
    .attr("d", "M0,-24 A24,24 0 0 0 0,24 L0,24 L0,-24 Z")
    .attr("fill", "#2ecc71");
  splitNodes.append("path")
    .attr("d", "M0,-24 A24,24 0 0 1 0,24 L0,24 L0,-24 Z")
    .attr("fill", "#e74c3c");
  splitNodes.append("circle")
    .attr("r", NODE_R)
    .attr("fill", "none");

  node.append("text")
    .attr("class", "label")
    .attr("x", 0)
    .attr("y", 0)
    .each(function(d) {{
      const lines = nodeLabelLines(d.label, 16);
      const t = d3.select(this);
      t.text(null);
      lines.forEach((line, i) => {{
        t.append("tspan")
          .attr("x", 0)
          .attr("dy", i === 0 ? (lines.length === 1 ? "0.35em" : "-0.2em") : "1.1em")
          .text(line);
      }});
    }});

  nodeSelection = node;
  edgeGroupSelection = edgeGroup;
  edgePathSelection = link;
  nodeIdsByEpisode = new Map();
  edgeKeysByEpisode = new Map();
  for (const n of renderNodes) {{
    for (const ep of (n.episode_uuids || [])) {{
      if (!nodeIdsByEpisode.has(ep)) nodeIdsByEpisode.set(ep, new Set());
      nodeIdsByEpisode.get(ep).add(String(n.id));
    }}
  }}
  for (const e of renderLinks) {{
    const edgeKey = `${{e.id}}-${{e.parallel_index}}`;
    for (const ep of (e.episode_uuids || [])) {{
      if (!edgeKeysByEpisode.has(ep)) edgeKeysByEpisode.set(ep, new Set());
      edgeKeysByEpisode.get(ep).add(edgeKey);
    }}
  }}
  resetGraphEpisodeHover();

  node.on("mousemove", (event, d) => {{
    tooltip.style("display", "block")
      .style("left", (event.offsetX) + "px")
      .style("top", (event.offsetY) + "px")
      .html(`<b>${{d.label}}</b>`);
    setHighlightForEpisodeUuids(d.episode_uuids || []);
  }}).on("mouseleave", () => {{
    tooltip.style("display", "none");
    setHighlightForEpisodeUuids([]);
    if (!graphEpisodeHoverActive) resetGraphEpisodeHover();
  }});

  link.on("mousemove", (event, d) => {{
    tooltip.style("display", "block")
      .style("left", (event.offsetX) + "px")
      .style("top", (event.offsetY) + "px")
      .html(`<b>${{d.label}}</b>`);
    setHighlightForEpisodeUuids(d.episode_uuids || []);
  }}).on("mouseleave", () => {{
    tooltip.style("display", "none");
    setHighlightForEpisodeUuids([]);
    if (!graphEpisodeHoverActive) resetGraphEpisodeHover();
  }});

  function dragged(event, d) {{
    d.x = event.x; d.y = event.y;
    posById.set(d.id, {{ x: d.x, y: d.y }});
    nodePos.set(d.id, {{ x: d.x, y: d.y }});
    d3.select(event.currentTarget).attr("transform", `translate(${{d.x}},${{d.y}})`);
    const affected = edgeGroup.filter(l => l.source === d.id || l.target === d.id);
    affected.selectAll("path")
      .each(function(l) {{
        const p = d3.select(this);
        const pid = p.attr("id") || "";
        if (pid.endsWith("-label")) {{
          p.attr("d", labelPathD(l, nodePos));
        }} else {{
          p.attr("d", linkPathD(l, nodePos));
        }}
      }});
  }}
}}

function renderTimeline() {{
  timelineSvg.selectAll("*").remove();
  const paneWidth = Math.max(240, timelineShell.clientWidth);
  const tlWidth = Math.max(220, paneWidth - 16);
  const tlHeight = 56;
  timelineSvg.attr("viewBox", [0, 0, tlWidth, tlHeight]);

  const margin = {{ left: 0, right: 0, top: 6, bottom: 4 }};
  const innerW = tlWidth - margin.left - margin.right;
  const innerH = tlHeight - margin.top - margin.bottom;
  const gT = timelineSvg.append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);

  const visible = visibleTimelineItems();
  const mods = visible.map(v => {{
    const m = frameMods(v.frameIdx);
    return {{ idx: v.slot, frameIdx: v.frameIdx, additions: m.add, deletions: m.del, total: m.total }};
  }});

  const maxTotal = Math.max(1, ...mods.map(m => m.total));
  const band = d3.scaleBand().domain(mods.map(m => m.idx)).range([0, innerW]).paddingInner(0.78).paddingOuter(0.0);
  const barWidth = Math.max(3, band.bandwidth() * 0.62);
  const y = d3.scaleLinear().domain([0, maxTotal]).range([innerH, 0]);

  gT.selectAll("line.spike")
    .data(mods)
    .join("line")
    .attr("class", "t-spike")
    .attr("x1", d => band(d.idx) + band.bandwidth() / 2)
    .attr("x2", d => band(d.idx) + band.bandwidth() / 2)
    .attr("y1", y(0))
    .attr("y2", d => y(d.total));

  const step = gT.selectAll("g.step")
    .data(mods)
    .join("g")
    .attr("class", "step");

  step.append("rect")
    .attr("class", "t-add")
    .attr("x", d => band(d.idx) + (band.bandwidth() - barWidth) / 2)
    .attr("y", d => y(d.additions))
    .attr("width", barWidth)
    .attr("height", d => Math.max(0, y(0) - y(d.additions)));

  step.append("rect")
    .attr("class", "t-del")
    .attr("x", d => band(d.idx) + (band.bandwidth() - barWidth) / 2)
    .attr("y", d => y(d.additions + d.deletions))
    .attr("width", barWidth)
    .attr("height", d => Math.max(0, y(d.additions) - y(d.additions + d.deletions)));

  step.append("rect")
    .attr("class", "t-click")
    .attr("x", d => band(d.idx) - 2)
    .attr("y", 0)
    .attr("width", band.bandwidth() + 4)
    .attr("height", innerH)
    .on("click", (_, d) => {{
      if (customWindow) return;
      if (d.frameIdx !== null && d.frameIdx !== undefined) setCurrentIdx(d.frameIdx);
    }});

  const visibleIdx = mods.findIndex(m => m.frameIdx === currentIdx);
  const currentSlot = visibleIdx >= 0 ? mods[visibleIdx].idx : 0;

  gT.append("rect")
    .attr("class", "t-current")
    .attr("x", band(currentSlot) + (band.bandwidth() - barWidth) / 2 - 2)
    .attr("y", 0)
    .attr("width", barWidth + 4)
    .attr("height", innerH);

  const slotFromX = (x) => {{
    const domain = band.domain();
    if (!domain.length) return 0;
    let bestSlot = domain[0];
    let bestDist = Infinity;
    domain.forEach(slot => {{
      const center = band(slot) + band.bandwidth() / 2;
      const dist = Math.abs(center - x);
      if (dist < bestDist) {{
        bestDist = dist;
        bestSlot = slot;
      }}
    }});
    return bestSlot;
  }};

  const brush = d3.brushX()
    .extent([[0, 0], [innerW, innerH]])
    .on("end", (event) => {{
      if (suppressBrushSync) return;
      const sel = event.selection;
      if (!sel) {{
        if (customWindow) clearCustomWindow();
        return;
      }}
      const [x0, x1] = sel;
      const startSlot = slotFromX(x0);
      const endSlot = slotFromX(x1);
      const minSlot = Math.min(startSlot, endSlot);
      const maxSlot = Math.max(startSlot, endSlot);
      const candidates = visible
        .filter(v => v.frameIdx !== null && v.frameIdx !== undefined)
        .filter(v => v.slot >= minSlot && v.slot <= maxSlot);
      if (!candidates.length) {{
        brushG.call(brush.move, null);
        if (customWindow) clearCustomWindow();
        return;
      }}
      const startIdx = candidates[0].frameIdx;
      const endIdx = candidates[candidates.length - 1].frameIdx;
      if (startIdx === undefined || endIdx === undefined) return;
      setCustomWindow(startIdx, endIdx);
    }});

  const brushG = gT.append("g").attr("class", "t-brush").call(brush);

  if (customWindow) {{
    const startSlot = slotForFrameIdx(customWindow.startIdx, visible);
    const endSlot = slotForFrameIdx(customWindow.endIdx, visible);
    if (startSlot !== null && endSlot !== null) {{
      suppressBrushSync = true;
      const a = Math.min(startSlot, endSlot);
      const b = Math.max(startSlot, endSlot);
      const x0 = band(a);
      const x1 = band(b) + band.bandwidth();
      brushG.call(brush.move, [x0, x1]);
      suppressBrushSync = false;
    }}
  }}
}}

function renderSliderSpikes() {{
  timelineSliderSpikesSvg.selectAll("*").remove();
  const paneWidth = Math.max(240, timelineShell.clientWidth);
  const sw = Math.max(220, paneWidth - 16);
  const sh = 24;
  timelineSliderSpikesSvg.attr("viewBox", [0, 0, sw, sh]);

  const margin = {{ left: 0, right: 0 }};
  const innerW = sw - margin.left - margin.right;
  const visible = visibleTimelineItems();
  const x = d3.scaleBand()
    .domain(visible.map(v => v.slot))
    .range([0, innerW])
    .paddingInner(0.78)
    .paddingOuter(0.0);

  const gS = timelineSliderSpikesSvg.append("g").attr("transform", `translate(${{margin.left}},0)`);
  const visibleIdx = visible.findIndex(v => v.frameIdx === currentIdx);
  const currentSlot = visibleIdx >= 0 ? visible[visibleIdx].slot : 0;
  const windowStartSlot = customWindow ? slotForFrameIdx(customWindow.startIdx, visible) : null;
  const windowEndSlot = customWindow ? slotForFrameIdx(customWindow.endIdx, visible) : null;
  const windowRange = (windowStartSlot !== null && windowEndSlot !== null)
    ? [Math.min(windowStartSlot, windowEndSlot), Math.max(windowStartSlot, windowEndSlot)]
    : null;
  const slotInWindow = slot => (windowRange ? (slot >= windowRange[0] && slot <= windowRange[1]) : false);

  gS.append("g")
    .selectAll("line")
    .data(visible)
    .join("line")
    .attr("x1", d => x(d.slot) + x.bandwidth() / 2)
    .attr("x2", d => x(d.slot) + x.bandwidth() / 2)
    .attr("y1", 3)
    .attr("y2", d => (d.slot === currentSlot ? 12 : 9))
    .attr("stroke", d => (
      d.slot === currentSlot ? "#2c7be5" : (slotInWindow(d.slot) ? "#f8b4ff" : "#7f8fa3")
    ))
    .attr("stroke-width", d => (d.slot === currentSlot ? 1.6 : 1.2))
    .attr("opacity", d => (slotInWindow(d.slot) ? 0.9 : (d.slot === currentSlot ? 0.95 : 0.7)));

  gS.append("g")
    .selectAll("text")
    .data(visible)
    .join("text")
    .attr("x", d => x(d.slot) + x.bandwidth() / 2)
    .attr("y", 20)
    .attr("text-anchor", "middle")
    .attr("font-size", "10px")
    .attr("fill", d => (
      d.slot === currentSlot ? "#dbe7ff" : (slotInWindow(d.slot) ? "#ffe0ff" : "#98a7bc")
    ))
    .text(d => d.tickLabel);
}}

function setCurrentIdx(idx) {{
  currentIdx = Math.max(0, Math.min(idx, Math.max(0, frames.length - 1)));
  if (isMonthGranularity && monthMeta[currentIdx]) {{
    activeYear = monthMeta[currentIdx].year;
  }}
  const visible = visibleTimelineItems();
  timelineSlider.min = "0";
  timelineSlider.max = String(Math.max(0, visible.length - 1));
  const slotPos = Math.max(0, visible.findIndex(v => v.frameIdx === currentIdx));
  timelineSlider.value = String(slotPos);
  setHighlightForEpisodeUuids([]);
  updateYearNav();
  renderTimeline();
  renderSliderSpikes();
  renderGraph();
  renderTabs();
}}

timelineSlider.addEventListener("input", (e) => {{
  if (customWindow) return;
  const slot = Number(e.target.value || 0);
  if (Number.isNaN(slot)) return;
  const visible = visibleTimelineItems();
  const target = visible[Math.max(0, Math.min(slot, visible.length - 1))];
  if (target && target.frameIdx !== null && target.frameIdx !== undefined) setCurrentIdx(target.frameIdx);
}});

if (windowClearBtn) {{
  windowClearBtn.addEventListener("click", () => clearCustomWindow());
}}

yearPrev.addEventListener("click", () => {{
  if (!isMonthGranularity) return;
  const i = availableYears.indexOf(activeYear);
  if (i <= 0) return;
  activeYear = availableYears[i - 1];
  const visible = visibleTimelineItems();
  const monthMatch = visible.find(v => v.frameIdx !== null && monthMeta[v.frameIdx] && monthMeta[v.frameIdx].month === 1);
  const fallback = visible.find(v => v.frameIdx !== null);
  if (monthMatch) setCurrentIdx(monthMatch.frameIdx);
  else if (fallback) setCurrentIdx(fallback.frameIdx);
  else {{
    updateYearNav();
    renderTimeline();
    renderSliderSpikes();
    renderTabs();
  }}
}});

yearNext.addEventListener("click", () => {{
  if (!isMonthGranularity) return;
  const i = availableYears.indexOf(activeYear);
  if (i < 0 || i >= availableYears.length - 1) return;
  activeYear = availableYears[i + 1];
  const visible = visibleTimelineItems();
  const monthMatch = visible.find(v => v.frameIdx !== null && monthMeta[v.frameIdx] && monthMeta[v.frameIdx].month === 1);
  const fallback = visible.find(v => v.frameIdx !== null);
  if (monthMatch) setCurrentIdx(monthMatch.frameIdx);
  else if (fallback) setCurrentIdx(fallback.frameIdx);
  else {{
    updateYearNav();
    renderTimeline();
    renderSliderSpikes();
    renderTabs();
  }}
}});

window.addEventListener("resize", () => {{
  updateYearNav();
  renderTimeline();
  renderSliderSpikes();
}});

const initVisible = visibleTimelineItems();
timelineSlider.min = "0";
timelineSlider.max = String(Math.max(0, initVisible.length - 1));
timelineSlider.step = "1";
timelineSlider.value = "0";
setCurrentIdx(currentIdx);
updateWindowSummary();
</script>
</body>
</html>
"""
