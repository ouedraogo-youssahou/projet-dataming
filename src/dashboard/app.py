"""
Smart eCommerce Intelligence
Design: Refined luxury-minimal — warm off-white, deep slate, brass accents.
Icons: Inline SVG (Lucide-style), no emoji.
"""

import logging, json, os, asyncio
from typing import Any, Dict, List, Optional
from decimal import Decimal
from pathlib import Path
from datetime import datetime

try: import nest_asyncio; nest_asyncio.apply()
except: pass

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

logger = logging.getLogger(__name__)
st.set_page_config(page_title="Smart eCommerce", page_icon="◈", layout="wide", initial_sidebar_state="expanded")

# ─── SVG ICON LIBRARY ──────────────────────────────────────────

def icon(name, size=16, color="currentColor", cls=""):
    """Inline SVG icons — simple single-path shapes, always render correctly."""
    s = size
    c = color
    icons = {
        "bar-chart":      f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="12" width="4" height="8"/><rect x="10" y="6" width="4" height="14"/><rect x="17" y="2" width="4" height="18"/></svg>',
        "tag":            f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><circle cx="7" cy="7" r="1.5" fill="{c}"/></svg>',
        "trending-up":    f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
        "award":          f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="9" r="6"/><path d="M8.21 13.89L7 23l5-3 5 3-1.21-9.11"/></svg>',
        "settings":       f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12"/></svg>',
        "message-square": f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
        "package":        f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22" x2="12" y2="12"/></svg>',
        "dollar-sign":    f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>',
        "star":           f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
        "users":          f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
        "grid":           f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>',
        "check-circle":   f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="9 12 11 14 15 10"/></svg>',
        "play":           f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="{c}" stroke="{c}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
        "activity":       f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
        "search":         f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
        "send":           f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>',
        "cpu":            f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>',
        "wifi":           f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><circle cx="12" cy="20" r="1" fill="{c}"/></svg>',
        "arrow-up":       f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>',
        "arrow-down":     f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>',
        "minus":          f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/></svg>',
        "layers":         f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
        "compass":        f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>',
        "shop":           f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>',
    }
    svg = icons.get(name, f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"><circle cx="12" cy="12" r="10"/></svg>')
    return f'<span class="icon-inline {cls}" style="display:inline-flex;align-items:center;vertical-align:middle;">{svg}</span>'

CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --bg:        #0D0F14;
        --bg-2:      #13151C;
        --surface:   #1A1D27;
        --surface-2: #20243180;
        --border:    #2A2E3F;
        --border-md: #363B52;
        --ink-0:     #F0F2FF;
        --ink-1:     #C8CDEE;
        --ink-2:     #8B93BC;
        --ink-3:     #535878;
        --ink-4:     #2E3249;
        --accent:    #00D4A1;
        --accent-dk: #00A87E;
        --accent-lt: #00D4A115;
        --accent-gl: #00D4A108;
        --indigo:    #6B7FFF;
        --indigo-lt: #6B7FFF12;
        --green:     #00D4A1;
        --green-lt:  #00D4A115;
        --red:       #FF5C7A;
        --red-lt:    #FF5C7A15;
        --yellow:    #FFB547;
        --yellow-lt: #FFB54715;
        --pink:      #D47BFF;
        --pink-lt:   #D47BFF15;
        --shadow-sm: 0 1px 4px rgba(0,0,0,0.4);
        --shadow-md: 0 4px 16px rgba(0,0,0,0.5), 0 1px 3px rgba(0,0,0,0.3);
        --shadow-glow: 0 0 20px rgba(0,212,161,0.08);
        --r-sm: 8px;
        --r-md: 12px;
        --r-lg: 16px;
    }

    * { font-family: 'Inter', sans-serif; box-sizing: border-box; }
    h1,h2,h3,h4,.pg-title,.stat-value,.app-header h1 { font-family: 'Syne', sans-serif !important; }
    code, pre, .mono { font-family: 'JetBrains Mono', monospace; }

    /* ── App shell ── */
    .stApp { background: var(--bg) !important; }
    .stApp::before {
        content: '';
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background:
            radial-gradient(ellipse 60% 40% at 80% 10%, rgba(0,212,161,0.04) 0%, transparent 60%),
            radial-gradient(ellipse 50% 50% at 10% 80%, rgba(107,127,255,0.04) 0%, transparent 60%);
        pointer-events: none; z-index: 0;
    }
    section[data-testid="stSidebar"] {
        background: var(--bg-2) !important;
        border-right: 1px solid var(--border) !important;
    }
    .main .block-container {
        padding: 0 1.5rem 2rem !important;
        max-width: 980px !important;
        position: relative; z-index: 1;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] .block-container { padding: 1.25rem 1rem !important; }
    .sidebar-logo {
        display: flex; align-items: center; gap: 0.6rem;
        padding: 0 0 1.1rem; margin-bottom: 1rem;
        border-bottom: 1px solid var(--border);
    }
    .sidebar-logo .mark {
        width: 34px; height: 34px;
        background: linear-gradient(135deg, #00D4A1, #00A87E);
        border-radius: 9px; display: flex; align-items: center; justify-content: center;
        flex-shrink: 0; box-shadow: 0 0 12px rgba(0,212,161,0.3);
    }
    .sidebar-logo h2 {
        font-family: 'Syne', sans-serif !important;
        font-size: 0.88rem; font-weight: 700; color: var(--ink-0); margin: 0; letter-spacing: -0.01em;
    }
    .sidebar-logo span { font-size: 0.68rem; color: var(--ink-3); display: block; font-weight: 400; }

    .sidebar-section {
        font-size: 0.62rem; font-weight: 600; color: var(--ink-3);
        text-transform: uppercase; letter-spacing: 0.1em;
        margin: 1.25rem 0 0.6rem;
    }

    /* Chat messages */
    div[data-testid="chatMessage"] {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--r-md) !important;
        padding: 0.55rem 0.75rem !important;
        margin-bottom: 0.35rem;
        box-shadow: none !important;
    }
    div[data-testid="chatMessage"] p {
        font-size: 0.82rem !important;
        color: var(--ink-1) !important;
        line-height: 1.55 !important;
    }
    div[data-testid="stChatInput"] {
        background: var(--surface) !important;
        border: 1px solid var(--border-md) !important;
        border-radius: var(--r-md) !important;
    }
    div[data-testid="stChatInput"]:focus-within {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(0,212,161,0.1) !important;
    }
    div[data-testid="stChatInput"] textarea {
        background: transparent !important;
        color: var(--ink-0) !important;
        font-size: 0.82rem !important;
    }

    /* ── Top header ── */
    .app-header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 1.25rem 0 0.5rem; margin-bottom: 0.5rem;
    }
    .app-header .wordmark { display: flex; align-items: center; gap: 0.65rem; }
    .app-header .mark {
        width: 38px; height: 38px;
        background: linear-gradient(135deg, #00D4A1, #00A87E);
        border-radius: var(--r-sm); display: flex; align-items: center; justify-content: center;
        box-shadow: 0 0 16px rgba(0,212,161,0.3);
    }
    .app-header h1 {
        font-size: 1.15rem; font-weight: 800; color: var(--ink-0); margin: 0; letter-spacing: -0.025em;
    }
    .app-header .badge {
        font-size: 0.68rem; font-weight: 600; padding: 0.22rem 0.6rem;
        border-radius: 20px; border: 1px solid var(--border);
        color: var(--ink-2); background: var(--surface);
    }
    .app-header .badge.live {
        color: var(--green); border-color: rgba(0,212,161,0.3);
        background: var(--green-lt);
    }

    /* ── Buttons ── */
    .stButton button {
        border-radius: var(--r-sm) !important;
        border: 1px solid var(--border-md) !important;
        background: var(--surface) !important;
        color: var(--ink-2) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.15s ease !important;
    }
    .stButton button:hover {
        border-color: var(--accent) !important;
        color: var(--accent) !important;
        background: var(--accent-gl) !important;
        box-shadow: 0 0 12px rgba(0,212,161,0.1) !important;
    }
    .stButton button[kind="primary"] {
        color: #0D0F14 !important;
        background: linear-gradient(135deg, #00D4A1, #00B88A) !important;
        border-color: transparent !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 12px rgba(0,212,161,0.3) !important;
    }
    .stButton button[kind="primary"]:hover {
        color: #0D0F14 !important;
        background: linear-gradient(135deg, #00E0AC, #00C495) !important;
        box-shadow: 0 4px 20px rgba(0,212,161,0.4) !important;
        transform: translateY(-1px) !important;
    }
    .stButton button[kind="secondary"] {
        color: var(--ink-2) !important;
        background: var(--surface) !important;
        border-color: var(--border) !important;
    }

    /* ── Page title ── */
    .pg-title {
        font-family: 'Syne', sans-serif !important;
        font-size: 1.4rem; font-weight: 800; color: var(--ink-0);
        margin: 0 0 0.15rem; letter-spacing: -0.03em;
    }
    .pg-sub { color: var(--ink-3); font-size: 0.78rem; margin-bottom: 1.25rem; font-weight: 400; }

    /* ── Stat cards ── */
    .stats-grid {
        display: grid; grid-template-columns: repeat(4, 1fr);
        gap: 0.75rem; margin-bottom: 1rem;
    }
    .stat-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--r-lg); padding: 1.1rem 1.15rem;
        box-shadow: var(--shadow-sm); position: relative; overflow: hidden;
        transition: border-color 0.2s, box-shadow 0.2s;
    }
    .stat-card:hover {
        border-color: var(--border-md);
        box-shadow: var(--shadow-md);
    }
    .stat-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0;
        height: 2px; background: var(--border);
    }
    .stat-card.accent::before { background: linear-gradient(90deg, #00D4A1, #00B88A); }
    .stat-card.green::before  { background: var(--green); }
    .stat-card.yellow::before { background: var(--yellow); }
    .stat-card.pink::before   { background: var(--pink); }
    .stat-card.accent { box-shadow: var(--shadow-glow); }
    .stat-icon {
        width: 32px; height: 32px; border-radius: var(--r-sm);
        background: var(--accent-lt); border: 1px solid rgba(0,212,161,0.2);
        display: flex; align-items: center; justify-content: center;
        margin-bottom: 0.7rem;
    }
    .stat-label {
        font-size: 0.62rem; font-weight: 600; color: var(--ink-3);
        text-transform: uppercase; letter-spacing: 0.09em; margin-bottom: 0.1rem;
    }
    .stat-value {
        font-size: 1.55rem; font-weight: 800; color: var(--ink-0);
        letter-spacing: -0.035em; line-height: 1;
    }
    .stat-foot { font-size: 0.65rem; color: var(--ink-3); margin-top: 0.3rem; }

    /* ── Data cards ── */
    .data-card {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: var(--r-md); padding: 1rem 1.1rem;
        margin-bottom: 0.65rem; box-shadow: var(--shadow-sm);
    }
    .data-card-label {
        font-size: 0.6rem; font-weight: 600; color: var(--ink-3);
        text-transform: uppercase; letter-spacing: 0.09em; margin-bottom: 0.3rem;
    }
    .data-card-header {
        font-family: 'Syne', sans-serif !important;
        font-size: 0.78rem; font-weight: 700; color: var(--ink-1);
        margin-bottom: 0.5rem; padding-bottom: 0.5rem;
        border-bottom: 1px solid var(--border);
        display: flex; align-items: center; gap: 0.4rem;
    }

    /* ── Progress bar ── */
    .prog-wrap { display: flex; align-items: center; gap: 0.65rem; margin-bottom: 0.9rem; }
    .prog-label { color: var(--ink-1); font-size: 0.74rem; white-space: nowrap; font-weight: 500; }
    .prog-track {
        flex: 1; background: var(--surface-2); border-radius: 20px;
        height: 5px; overflow: hidden; border: 1px solid var(--border);
    }
    .prog-fill {
        height: 100%; border-radius: 20px;
        background: linear-gradient(90deg, #00D4A1, #00B88A);
        box-shadow: 0 0 8px rgba(0,212,161,0.4);
        transition: width 0.5s ease;
    }
    .prog-val { font-weight: 700; font-size: 0.76rem; color: var(--accent); white-space: nowrap; }

    /* ── Table ── */
    div[data-testid="stDataFrame"] {
        border: 1px solid var(--border) !important;
        border-radius: var(--r-md) !important;
        overflow: hidden; box-shadow: var(--shadow-sm);
    }
    div[data-testid="stDataFrame"] thead tr th {
        background: var(--surface) !important; color: var(--ink-2) !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important; font-size: 0.63rem !important;
        text-transform: uppercase; letter-spacing: 0.08em;
        border-bottom: 1px solid var(--border) !important;
        padding: 0.5rem 0.75rem !important;
    }
    div[data-testid="stDataFrame"] tbody tr td {
        color: var(--ink-1) !important; font-size: 0.82rem !important;
        border-bottom: 1px solid var(--border) !important;
        padding: 0.4rem 0.75rem !important;
        background: var(--bg-2) !important;
    }
    div[data-testid="stDataFrame"] tbody tr:hover td {
        background: var(--surface) !important;
        color: var(--ink-0) !important;
    }

    /* ── Expanders ── */
    div[data-testid="stExpander"] {
        border: 1px solid var(--border) !important;
        border-radius: var(--r-md) !important;
        margin-bottom: 0.5rem !important;
        background: var(--surface); box-shadow: var(--shadow-sm); overflow: hidden;
    }
    div[data-testid="stExpander"] summary {
        font-size: 0.83rem !important; font-weight: 600 !important;
        color: var(--ink-1) !important; padding: 0.65rem 0.85rem !important;
        background: var(--bg-2) !important;
    }

    /* ── Tabs ── */
    div[data-testid="stTabs"] {
        border-bottom: 1px solid var(--border); margin-bottom: 1rem;
    }
    div[data-testid="stTabs"] button {
        color: var(--ink-3) !important; font-weight: 500 !important;
        font-size: 0.8rem !important; padding: 0.4rem 0.85rem !important;
        border-bottom: 2px solid transparent !important;
        border-radius: 0 !important; background: transparent !important;
        transition: color 0.15s !important;
    }
    div[data-testid="stTabs"] button:hover { color: var(--ink-1) !important; }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--accent) !important;
        border-bottom-color: var(--accent) !important;
        font-weight: 600 !important;
    }

    /* ── Alerts ── */
    div.stAlert {
        border-radius: var(--r-md) !important;
        border: 1px solid var(--border) !important;
        background: var(--surface) !important;
        font-size: 0.82rem !important; color: var(--ink-1) !important;
    }

    /* ── Selectbox & sliders ── */
    div[data-testid="stSelectbox"] select,
    div[data-testid="stSelectbox"] > div > div {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--r-sm) !important;
        color: var(--ink-0) !important;
        font-size: 0.82rem !important;
    }
    div[data-testid="stSlider"] > div > div > div { background: var(--accent) !important; }

    /* ── Radio ── */
    div[data-testid="stRadio"] label { font-size: 0.82rem !important; color: var(--ink-1) !important; }

    /* ── HR ── */
    hr { border-color: var(--border) !important; margin: 0.75rem 0 !important; }

    /* ── Metrics ── */
    div[data-testid="stMetric"] {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--r-md) !important;
        padding: 0.75rem 1rem !important;
    }
    div[data-testid="stMetric"] label { color: var(--ink-3) !important; font-size: 0.7rem !important; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: var(--ink-0) !important; font-family: 'Syne', sans-serif !important; }

    /* ── Footer ── */
    .app-footer {
        color: var(--ink-3); font-size: 0.65rem; text-align: center;
        padding: 1.5rem 0 0.5rem; border-top: 1px solid var(--border);
        margin-top: 2rem; letter-spacing: 0.06em; text-transform: uppercase; font-weight: 500;
    }

    /* Inline icon alignment */
    .icon-emoji { display: inline-flex; align-items: center; vertical-align: middle; }
    .icon-inline { display: inline-flex; align-items: center; vertical-align: middle; }
    .with-icon { display: flex; align-items: center; gap: 0.4rem; }

    /* Trend badges */
    .trend-badge {
        display: inline-flex; align-items: center; gap: 0.25rem;
        font-size: 0.68rem; font-weight: 600; padding: 0.18rem 0.5rem;
        border-radius: 20px;
    }
    .trend-up   { color: var(--green); background: var(--green-lt); border: 1px solid rgba(0,212,161,0.2); }
    .trend-down { color: var(--red);   background: var(--red-lt);   border: 1px solid rgba(255,92,122,0.2); }
    .trend-flat { color: var(--ink-2); background: var(--surface);  border: 1px solid var(--border); }

    /* Segment row */
    .seg-row {
        display: flex; align-items: center; justify-content: space-between;
        padding: 0.55rem 0.8rem; border-radius: var(--r-sm);
        background: var(--bg-2); border: 1px solid var(--border);
        margin-bottom: 0.35rem; transition: border-color 0.15s;
    }
    .seg-row:hover { border-color: var(--border-md); }
    .seg-name { font-weight: 600; font-size: 0.82rem; color: var(--ink-0); }
    .seg-meta { font-size: 0.68rem; color: var(--ink-3); margin-top: 0.05rem; }
    .seg-score { font-family: 'JetBrains Mono', monospace; font-size: 0.76rem; color: var(--accent); font-weight: 500; }

    /* MCP endpoint rows */
    .ep-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.38rem 0; border-bottom: 1px solid var(--border);
        font-size: 0.78rem;
    }
    .ep-row:last-child { border-bottom: none; }
    .ep-path { font-family: 'JetBrains Mono', monospace; color: var(--accent); font-size: 0.72rem; font-weight: 500; }
    .ep-desc { color: var(--ink-3); font-size: 0.7rem; }

    /* Pipeline status */
    .pipe-steps { display: flex; align-items: center; gap: 0; margin: 0.75rem 0; }
    .pipe-step {
        flex: 1; text-align: center; position: relative;
        font-size: 0.68rem; color: var(--ink-3); font-weight: 500;
    }
    .pipe-step-dot {
        width: 10px; height: 10px; border-radius: 50%;
        background: var(--border); margin: 0 auto 0.3rem; position: relative; z-index: 1;
    }
    .pipe-step-dot.done {
        background: var(--accent);
        box-shadow: 0 0 8px rgba(0,212,161,0.5);
    }
    .pipe-step::after {
        content: ''; position: absolute; top: 5px; left: 50%; right: -50%;
        height: 1px; background: var(--border); z-index: 0;
    }
    .pipe-step:last-child::after { display: none; }

    /* Spinner */
    div[data-testid="stSpinner"] { color: var(--accent) !important; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: var(--border-md); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--ink-3); }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ─── HELPERS ──────────────────────────────────────────────────

def load_products_from_db():
    try:
        import asyncpg
        h=os.getenv("POSTGRES_HOST","postgres"); u=os.getenv("POSTGRES_USER","ecommerce_user"); p=os.getenv("POSTGRES_PASSWORD","secure_password")
        async def f():
            c=await asyncpg.connect(host=h,port=5432,database="ecommerce_db",user=u,password=p)
            r=await c.fetch("SELECT * FROM products ORDER BY price DESC"); await c.close()
            return [_c(dict(x)) for x in r]
        return asyncio.run(f())
    except Exception as e:
        logger.warning(f"DB load error: {e}")
        return None

def _c(p):
    for c in ['price','rating','reviews_count']:
        v=p.get(c)
        if v is None: p[c]=0.0 if c!='reviews_count' else 0
        elif isinstance(v,Decimal): p[c]=float(v) if c!='reviews_count' else int(v)
        elif isinstance(v,str):
            try: p[c]=float(v) if c!='reviews_count' else int(float(v))
            except: p[c]=0.0 if c!='reviews_count' else 0
        elif isinstance(v,(int,float)): p[c]=float(v) if c!='reviews_count' else int(v)
        else:
            try: p[c]=float(v) if c!='reviews_count' else int(float(v))
            except: p[c]=0.0 if c!='reviews_count' else 0
    if 'availability' in p:
        a=p['availability']
        if isinstance(a,str): p['availability']=a.lower() in ('true','1','yes')
        elif isinstance(a,(int,float)): p['availability']=bool(a)
    return p

def load_products():
    db=load_products_from_db()
    if db and len(db)>0: return db,"PostgreSQL"
    for sp in [Path("data/raw/products.json"),Path("/app/data/raw/products.json")]:
        if sp.exists():
            try:
                with open(sp) as f: d=json.load(f)
                if isinstance(d,list) and len(d)>0: return d,sp.name
            except: pass
    return [
        {"product_id":"1","name":"Wireless Earbuds","category":"Electronics","price":59,"rating":4.6,"reviews_count":1200,"availability":True},
        {"product_id":"2","name":"Fitness Tracker","category":"Sport","price":49,"rating":4.2,"reviews_count":340,"availability":True},
        {"product_id":"3","name":"LED Desk Lamp","category":"Home","price":29,"rating":4.8,"reviews_count":980,"availability":True}
    ],"Sample"

def topk(products, k=10, w=None):
    w=w or {"rating":0.3,"reviews_count":0.25,"price_competitiveness":0.2,"availability":0.15}
    df=pd.DataFrame(products)
    if df.empty: return pd.DataFrame()
    for c in ['price','rating','reviews_count']:
        if c in df.columns: df[c]=pd.to_numeric(df[c],errors='coerce').fillna(0).astype(float)
    if 'availability' in df.columns: df['availability']=df['availability'].astype(float)
    mp=df['price'].max() or 1; mr=df['rating'].max() or 5; mv=df['reviews_count'].max() or 1
    df['_s']=(w["rating"]*(df['rating']/mr)+w["reviews_count"]*(df['reviews_count']/mv)+w["price_competitiveness"]*(1-df['price']/mp)+w["availability"]*df['availability'])
    return df.sort_values('_s',ascending=False).head(k)

@st.cache_resource
def llm():
    from src.llm.wrapper import LLMWrapper
    return LLMWrapper(deepseek_key=os.getenv("DEEPSEEK_API_KEY"),groq_key=os.getenv("GROQ_API_KEY"))

def ask(prompt, products=None):
    w=llm()
    if products and len(products)>0:
        ctx=f"Assistant eCommerce. {len(products)} produits.\n"+'\n'.join([f"- {p.get('name','?')} | {p.get('price',0):.0f}$" for p in products[:50]])+f"\n\nQuestion: {prompt}"
    else: ctx=f"Réponds: {prompt}"
    try: return w.complete(ctx,provider="groq",max_tokens=800)
    except RuntimeError as e:
        if "No LLM provider" in str(e): return "GROQ_API_KEY manquante"
        raise
    except: return "Erreur lors de la requête"

# ─── PLOT THEME ───────────────────────────────────────────────

PLOT_COLORS = ["#6366F1","#F59E0B","#10B981","#EF4444","#8B5CF6","#3B82F6","#EC4899","#14B8A6"]

def plot_layout(fig, height=280, margin=None):
    m = margin or dict(l=8, r=8, t=36, b=16)
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#6366F1', family='DM Sans'),
        title_font=dict(color='#1E1B4B', size=13, family='DM Sans'),
        height=height, margin=m,
        legend=dict(bgcolor='rgba(0,0,0,0)', borderwidth=0, font=dict(size=11)),
        xaxis=dict(gridcolor='#D6E0FF', linecolor='#B8C8FF', tickfont=dict(size=10)),
        yaxis=dict(gridcolor='#D6E0FF', linecolor='#B8C8FF', tickfont=dict(size=10)),
    )
    return fig

# ─── PAGES ────────────────────────────────────────────────────

def pg_overview(products, src):
    st.markdown(f'<div class="pg-title">Vue d\'ensemble</div>', unsafe_allow_html=True)
    

    df=pd.DataFrame(products)
    for c in ['price','rating','reviews_count']:
        if c in df.columns: df[c]=pd.to_numeric(df[c],errors='coerce').fillna(0)

    ap=df['price'].mean(); ar=df['rating'].mean()
    tr=int(df['reviews_count'].sum()); nc=df['category'].nunique() if 'category' in df.columns else 0
    av=(df['availability'].sum()/len(df)*100) if 'availability' in df.columns and len(df)>0 else 0

    pkg = icon("package", 14, "#7A7168")
    dol = icon("dollar-sign", 14, "#7A7168")
    star = icon("star", 14, "#7A7168")
    usr = icon("users", 14, "#7A7168")

    st.markdown(f'''
    <div class="stats-grid">
        <div class="stat-card accent">
            <div class="stat-icon">{pkg}</div>
            <div class="stat-label">Produits</div>
            <div class="stat-value">{len(df)}</div>
            <div class="stat-foot">{nc} catégories</div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">{dol}</div>
            <div class="stat-label">Prix moyen</div>
            <div class="stat-value">{ap:.0f}<span style="font-size:0.8rem;font-weight:400;color:var(--ink-3);">$</span></div>
            <div class="stat-foot">Médiane catalogue</div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">{star}</div>
            <div class="stat-label">Note moyenne</div>
            <div class="stat-value">{ar:.2f}<span style="font-size:0.8rem;font-weight:400;color:var(--ink-3);">/5</span></div>
            <div class="stat-foot">Toutes catégories</div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">{usr}</div>
            <div class="stat-label">Avis totaux</div>
            <div class="stat-value">{tr:,}</div>
            <div class="stat-foot">Cumulés</div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    if av > 0:
        st.markdown(f'''
        <div class="prog-wrap">
            <span class="prog-label">{icon("check-circle", 13, "#7A7168")} Disponibilité</span>
            <div class="prog-track"><div class="prog-fill" style="width:{av:.0f}%;"></div></div>
            <span class="prog-val">{av:.0f}%</span>
        </div>
        ''', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        fig=px.scatter(df, x='price', y='rating', color='category', size='reviews_count',
                       hover_name='name', title="Prix vs Note",
                       color_discrete_sequence=PLOT_COLORS)
        st.plotly_chart(plot_layout(fig), use_container_width=True)
    with c2:
        cc=df['category'].value_counts().reset_index(); cc.columns=['category','count']
        fig=px.pie(cc, values='count', names='category', title="Répartition catégories",
                   color_discrete_sequence=PLOT_COLORS, hole=0.42)
        fig.update_traces(textposition='inside', textinfo='percent', textfont_size=11)
        st.plotly_chart(plot_layout(fig), use_container_width=True)


def pg_topk(products):
    st.markdown('<div class="pg-title">Classement produits</div>', unsafe_allow_html=True)
    st.markdown('<div class="pg-sub">Score pondéré : note · avis · compétitivité prix · disponibilité.</div>', unsafe_allow_html=True)

    df=pd.DataFrame(products)
    for c in ['price','rating','reviews_count']:
        if c in df.columns: df[c]=pd.to_numeric(df[c],errors='coerce').fillna(0)

    cf, ct = st.columns([1,3])
    with cf:
        cats=["Tous"]+sorted(df['category'].dropna().unique().tolist())
        cat=st.selectbox("Catégorie", cats, label_visibility="visible")
        k=st.slider("Afficher", 1, min(20,len(df)), 10, label_visibility="visible")
        mx=int(df['price'].max()); pr=st.slider("Prix max ($)", 0, mx, mx, label_visibility="visible")

    mask=(df['price']>=0)&(df['price']<=pr)
    if cat!="Tous": mask&=(df['category']==cat)
    df_top=topk(df[mask].to_dict('records'), k=k)

    if not df_top.empty:
        d=df_top[["name","category","price","rating","reviews_count","_s"]].copy()
        d=d.rename(columns={"name":"Produit","category":"Catégorie","price":"Prix ($)","rating":"Note","reviews_count":"Avis","_s":"Score"})
        d["Score"]=d["Score"].round(4)
        st.dataframe(d, use_container_width=True, hide_index=True)
    else:
        st.warning("Aucun produit ne correspond aux filtres.")


def pg_ml(products):
    st.markdown('<div class="pg-title">Analyses & Modèles</div>', unsafe_allow_html=True)
    st.markdown('<div class="pg-sub">Clustering, prévisions de prix, tendances émergentes.</div>', unsafe_allow_html=True)

    df=pd.DataFrame(products)
    for c in ['price','rating','reviews_count']:
        if c in df.columns: df[c]=pd.to_numeric(df[c],errors='coerce').fillna(0)

    from src.data_analysis import generate_trend_insights
    ti=generate_trend_insights(products)
    t1,t2,t3=st.tabs(["Clustering", "Prévisions de prix", "Tendances"])

    with t1:
        from sklearn.preprocessing import StandardScaler; from sklearn.decomposition import PCA
        import base64,io,joblib,numpy as np
        X=df[['price','rating','reviews_count']].fillna(0).values; Xs=StandardScaler().fit_transform(X)
        models={}
        for mn in ['kmeans','dbscan','random_forest']:
            try:
                import asyncpg
                async def _ld(n=mn):
                    conn=await asyncpg.connect(host=os.getenv("POSTGRES_HOST","postgres"),port=5432,database="ecommerce_db",user=os.getenv("POSTGRES_USER","ecommerce_user"),password=os.getenv("POSTGRES_PASSWORD","secure_password"))
                    row=await conn.fetchrow("SELECT model_data FROM kfp_models WHERE model_name=$1 ORDER BY created_at DESC LIMIT 1",n); await conn.close()
                    return joblib.load(io.BytesIO(base64.b64decode(row['model_data']))) if row else None
                models[mn]=asyncio.run(_ld())
            except: pass

        mc=st.radio("Algorithme", ["PCA","KMeans","DBSCAN","RF"], horizontal=True, key="mc")

        if mc=="PCA":
            pca=PCA(n_components=2); Xp=pca.fit_transform(Xs); df['_x'],df['_y']=Xp[:,0],Xp[:,1]
            fig=px.scatter(df,x='_x',y='_y',color='category',hover_name='name',
                           title=f"Analyse PCA — variance expliquée {pca.explained_variance_ratio_.sum()*100:.0f}%",
                           color_discrete_sequence=PLOT_COLORS)
            st.plotly_chart(plot_layout(fig), use_container_width=True)
        elif mc=="KMeans" and models.get('kmeans'):
            m=models['kmeans']; df['_cl']=m.predict(Xs).astype(str)
            fig=px.scatter(df,x='price',y='rating',color='_cl',hover_name='name',
                           title=f"KMeans — {m.n_clusters} clusters",color_discrete_sequence=PLOT_COLORS)
            st.plotly_chart(plot_layout(fig), use_container_width=True)
        elif mc=="DBSCAN" and models.get('dbscan'):
            m=models['dbscan']; l=m.fit_predict(Xs); df['_cl']=l.astype(str)
            fig=px.scatter(df[l!=-1],x='price',y='rating',color='_cl',hover_name='name',
                           title="DBSCAN Clustering",color_discrete_sequence=PLOT_COLORS)
            st.plotly_chart(plot_layout(fig), use_container_width=True)
        elif mc=="RF" and models.get('random_forest'):
            m=models['random_forest']; df['_cl']=m.predict(Xs).astype(str)
            fig=px.scatter(df,x='price',y='rating',color='_cl',hover_name='name',
                           title="Random Forest — Prédictions",color_discrete_sequence=PLOT_COLORS)
            st.plotly_chart(plot_layout(fig), use_container_width=True)
        else:
            from sklearn.cluster import KMeans,DBSCAN; from sklearn.ensemble import RandomForestClassifier
            if mc=="KMeans": l=KMeans(n_clusters=min(4,len(df)),random_state=42,n_init=10).fit_predict(Xs)
            elif mc=="DBSCAN": l=DBSCAN(eps=0.5,min_samples=5).fit_predict(Xs)
            else: l=RandomForestClassifier(n_estimators=50,random_state=42).fit(Xs,(X[:,0]>np.median(X[:,0])).astype(int)).predict(Xs)
            df['_cl']=l.astype(str)
            fig=px.scatter(df,x='price',y='rating',color='_cl',hover_name='name',
                           title=mc,color_discrete_sequence=PLOT_COLORS)
            st.plotly_chart(plot_layout(fig), use_container_width=True)

    with t2:
        fc=ti.get('category_price_forecasts',{}); tr=ti.get('category_price_trends',{})
        if fc:
            cat=st.selectbox("Catégorie", list(fc.keys()), key="pc")
            c1,c2=st.columns([2,1])
            with c1:
                f=fc[cat]
                fig=go.Figure()
                fig.add_trace(go.Scatter(x=f['dates'],y=f['values'],mode='lines+markers',name='Prévision 30j',
                                         line=dict(color='#1A1714',width=2,dash='dash'),
                                         marker=dict(size=4,color='#1A1714')))
                fig.add_trace(go.Scatter(x=f['dates']+f['dates'][::-1],y=f['upper']+f['lower'][::-1],
                                         fill='toself',fillcolor='rgba(166,124,82,0.08)',
                                         line=dict(color='rgba(0,0,0,0)'),hoverinfo="skip",name='Intervalle confiance'))
                fig.update_layout(title=f"Prévision de prix — {cat}",xaxis_title="Date",yaxis_title="Prix ($)",hovermode='x unified')
                st.plotly_chart(plot_layout(fig,height=260), use_container_width=True)
            with c2:
                ci=tr.get(cat,{})
                if ci:
                    trend=ci.get("trend","N/A")
                    if trend=="growing": badge=f'<span class="trend-badge trend-up">{icon("arrow-up",11,"#2D6A4F")} Croissance</span>'
                    elif trend=="declining": badge=f'<span class="trend-badge trend-down">{icon("arrow-down",11,"#9B2335")} Déclin</span>'
                    else: badge=f'<span class="trend-badge trend-flat">{icon("minus",11,"#7A7168")} Stable</span>'
                    st.markdown(f'''
                    <div class="data-card">
                        <div class="data-card-label">Tendance</div>
                        <div style="margin:0.3rem 0 0.6rem;">{badge}</div>
                        <div class="data-card-label" style="margin-top:0.5rem;">Prix moyen</div>
                        <div style="font-size:1.1rem;font-weight:700;color:var(--ink-0);">${ci.get("avg_price",0):.2f}</div>
                    </div>
                    ''', unsafe_allow_html=True)
        else:
            st.info("Au moins 5 produits par catégorie sont requis pour les prévisions.")

    with t3:
        tr=ti.get('trending_products',[]); acc=ti.get('xgboost_accuracy')
        ca,cb=st.columns([1,2])
        with ca:
            if tr and len(products)>=30:
                st.metric("Accuracy XGBoost", f"{acc:.1%}" if acc else "N/A")
            elif len(products)>=30: st.info("Modèle non disponible")
            else: st.warning(f"Minimum 30 produits requis ({len(products)} actuellement)")
        with cb:
            if tr:
                for i,p in enumerate(tr[:5],1):
                    st.markdown(f'<div style="font-size:0.8rem;padding:0.2rem 0;border-bottom:1px solid var(--border);"><span style="color:var(--ink-3);font-family:\'DM Mono\',monospace;">{i:02d}</span>  <strong>{p["name"]}</strong>  <span style="color:var(--brass);font-family:\'DM Mono\',monospace;float:right;">{p["score"]:.3f}</span></div>', unsafe_allow_html=True)
            else: st.info("Aucun produit tendance identifié.")
        if tr:
            sdf=pd.DataFrame(tr[:8])
            fig=px.bar(sdf,x='name',y='score',color='score',color_continuous_scale=[[0,'#C7D2FE'],[1,'#6366F1']],labels={'name':'','score':''})            
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(plot_layout(fig,height=180,margin=dict(l=5,r=5,t=10,b=30)), use_container_width=True)


def pg_competitive(products):
    st.markdown('<div class="pg-title">Intelligence concurrentielle</div>', unsafe_allow_html=True)
    st.markdown('<div class="pg-sub">Analyses comparatives, produits émergents, recommandations stratégiques.</div>', unsafe_allow_html=True)

    from src.llm.competitive_analysis import CompetitiveAnalysis
    gk=os.getenv("GROQ_API_KEY","")
    if not gk: st.warning("Clé GROQ_API_KEY manquante — configurez votre .env"); return
    if not products: st.info("Aucun produit chargé."); return

    b1,b2,b3,_=st.columns([1,1,1,1.5])
    with b1:
        r1 = st.button("⊕ Comparer", type="primary", use_container_width=True, key="c1")
    with b2:
        r2 = st.button("↗ Émergents", use_container_width=True, key="c2")
    with b3:
        r3 = st.button("◈ Stratégie", use_container_width=True, key="c3")

    if "cr" not in st.session_state: st.session_state.cr={}

    try:
        an=CompetitiveAnalysis(groq_key=gk)

        if r1 or st.session_state.get("cs1"):
            st.session_state.cs1=True
            if "cmp" not in st.session_state.cr:
                with st.spinner("Analyse en cours…"): st.session_state.cr["cmp"]=an.compare_products(products)
            res=st.session_state.cr["cmp"]
            if res.get("status")=="completed":
                for comp in res.get("comparisons",[]):
                    with st.expander(f"{comp['category']} — {comp['products_compared']} produits", expanded=True):
                        ca,cb=st.columns([1,2])
                        with ca:
                            st.markdown(f'''
                            <div class="data-card">
                                <div class="data-card-label">Prix moyen</div>
                                <div style="font-size:1.1rem;font-weight:700;color:var(--ink-0);margin-bottom:0.5rem;">${comp["price_range"]["avg"]:.0f}</div>
                                <div class="data-card-label">Note</div>
                                <div style="font-size:1.1rem;font-weight:700;color:var(--ink-0);">{comp["avg_rating"]:.2f} <span style="color:var(--ink-3);font-size:0.75rem;">/5</span></div>
                            </div>
                            ''', unsafe_allow_html=True)
                        with cb:
                            st.markdown(f'<div class="data-card" style="font-size:0.8rem;color:var(--ink-1);line-height:1.6;">{comp.get("analysis_text","")}</div>', unsafe_allow_html=True)
            else: st.info(res.get("message",""))

        if r2 or st.session_state.get("cs2"):
            st.session_state.cs2=True
            if "emg" not in st.session_state.cr:
                with st.spinner("Analyse en cours…"): st.session_state.cr["emg"]=an.generate_emerging_report(products)
            res=st.session_state.cr["emg"]
            if res.get("status")=="completed":
                el=res.get("emerging_products",[])
                if el:
                    edf=pd.DataFrame(el)
                    cols=[c for c in ["rank","name","category","price","rating","reviews_count","emergence_score"] if c in edf.columns]
                    disp=edf[cols].rename(columns={"rank":"#","name":"Produit","category":"Catégorie","price":"Prix ($)","rating":"Note","reviews_count":"Avis","emergence_score":"Score"})
                    st.dataframe(disp, use_container_width=True, hide_index=True)
                    fig=px.bar(edf,x='name',y='emergence_score',color='emergence_score',
                               color_continuous_scale=[[0,'#A5B4FC'],[1,'#6366F1']],
                               labels={'name':'','emergence_score':''})
                    fig.update_layout(coloraxis_showscale=False)
                    st.plotly_chart(plot_layout(fig,height=180,margin=dict(l=5,r=5,t=10,b=30)), use_container_width=True)
                rt=res.get("report_text","")
                if rt: st.markdown(f'<div class="data-card" style="font-size:0.8rem;color:var(--ink-1);line-height:1.6;">{rt}</div>', unsafe_allow_html=True)
            else: st.info(res.get("message",""))

        if r3 or st.session_state.get("cs3"):
            st.session_state.cs3=True
            if "rec" not in st.session_state.cr:
                with st.spinner("Analyse en cours…"): st.session_state.cr["rec"]=an.generate_strategic_recommendations(products)
            res=st.session_state.cr["rec"]
            if res.get("status")=="completed":
                segs=res.get("segments",[])
                if segs:
                    for s in segs[:5]:
                        st.markdown(f'''
                        <div class="seg-row">
                            <div>
                                <div class="seg-name">{s["category"]}</div>
                                <div class="seg-meta">{s["product_count"]} produits · ${s["avg_price"]:.0f} · {s["avg_rating"]}/5</div>
                            </div>
                            <div class="seg-score">{s["value_score"]:.3f}</div>
                        </div>
                        ''', unsafe_allow_html=True)
                rt=res.get("recommendations_text","")
                if rt: st.markdown(f'<div class="data-card" style="margin-top:0.75rem;font-size:0.8rem;color:var(--ink-1);line-height:1.6;">{rt}</div>', unsafe_allow_html=True)
            else: st.info(res.get("message",""))

    except Exception as e:
        st.error(f"Erreur : {str(e)}")
        logger.error(f"Competitive analysis error: {e}", exc_info=True)


def pg_infra():
    st.markdown('<div class="pg-title">Infrastructure</div>', unsafe_allow_html=True)
    st.markdown('<div class="pg-sub">Pipeline ML · Services MCP · Orchestration.</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(f'''
        <div class="data-card">
            <div class="data-card-header">{icon("activity",14,"#7A7168")} Pipeline ML</div>
            <div class="pipe-steps">
                <div class="pipe-step"><div class="pipe-step-dot done"></div>Scraping</div>
                <div class="pipe-step"><div class="pipe-step-dot done"></div>Prep</div>
                <div class="pipe-step"><div class="pipe-step-dot"></div>ML</div>
                <div class="pipe-step"><div class="pipe-step-dot"></div>Base</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

        if st.button("▶ Lancer le pipeline", type="primary", use_container_width=True):
            with st.spinner("Exécution en cours…"):
                try:
                    import subprocess
                    h=os.getenv("KFP_HOST","http://host.docker.internal:61567")
                    r=subprocess.run(["python","scripts/run_kfp.py","--host",h],
                                     capture_output=True,text=True,timeout=120,cwd="/app")
                    if r.returncode==0:
                        st.success("Pipeline exécuté avec succès")
                        st.code(r.stdout[-200:] if len(r.stdout)>200 else r.stdout)
                    else:
                        st.error(f"Erreur : {r.stderr[-200:]}")
                except subprocess.TimeoutExpired: st.warning("Délai d'exécution dépassé")
                except Exception as e: st.error(f"Erreur : {str(e)}")

    with c2:
        eps=[
            ("GET /health","Health check"),
            ("/tools/scrape_shopify","Shopify scraper"),
            ("/tools/scrape_woocommerce","WooCommerce scraper"),
            ("/tools/analyze_top_k","Classement Top-K"),
            ("/tools/competitive_analysis","Analyse concurrence"),
        ]
        rows_html=''.join([f'<div class="ep-row"><span class="ep-path">{e}</span><span class="ep-desc">{d}</span></div>' for e,d in eps])
        st.markdown(f'''
        <div class="data-card">
            <div class="data-card-header">{icon("wifi",14,"#7A7168")} Endpoints MCP <span style="color:var(--ink-3);font-size:0.68rem;margin-left:auto;font-family:\'DM Mono\',monospace;">:8000</span></div>
            {rows_html}
        </div>
        ''', unsafe_allow_html=True)


# ─── MAIN ─────────────────────────────────────────────────────

def main():
    if "page" not in st.session_state: st.session_state.page="overview"

    p, s = load_products()
    st.session_state.pc = p
    st.session_state.sc = s
    products = p
    source = s

    if not isinstance(products, list) or len(products) == 0:
        products = []
        st.warning("Aucune donnée produit disponible.")

    # ── SIDEBAR ──
    with st.sidebar:
        from pathlib import Path


        st.markdown(f'''
        <div class="sidebar-logo">
            <div class="mark">{icon("shop", 16, "#FFFFFF")}</div>
            <div>
                <h2>Smart eCommerce</h2>
                <span>Intelligence produit</span>
            </div>
        </div>
        ''', unsafe_allow_html=True)
        LOGO_PATH = Path(__file__).parent / "images" / "image_3.png"
        if LOGO_PATH.exists():
         st.image(str(LOGO_PATH), use_container_width=True)
        else:
            st.warning("Logo not found")

        st.markdown(f'<div class="sidebar-section">{icon("message-square", 13, "#6366F1")} Assistant IA</div>', unsafe_allow_html=True)

        if "ch" not in st.session_state: st.session_state.ch=[]
        for msg in st.session_state.ch[-6:]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if pr := st.chat_input("Posez une question sur les produits…"):
            st.session_state.ch.append({"role":"user","content":pr})
            with st.chat_message("user"): st.markdown(pr)
            with st.chat_message("assistant"):
                with st.spinner(""):
                    r = ask(pr, products)
                st.markdown(r)
            st.session_state.ch.append({"role":"assistant","content":r})

  

    st.markdown(f'''
    <div class="app-header">
        <div class="wordmark">
            <div class="mark">{icon("shop", 18, "#FFFFFF")}</div>
            <h1>Smart eCommerce</h1>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    # ── NAV ──
    pages=[
        (icon("bar-chart",13),"Vue d'ensemble","overview"),
        (icon("tag",13),"Les Top-K produits","topk"),
        (icon("trending-up",13),"Machine Learning","analysis"),
        (icon("award",13),"Analyse concurrentielle","competitive"),
        (icon("settings",13),"Orchestration MCP","infra"),
    ]

    cols=st.columns(len(pages))
    for i,(ic_svg,label,key) in enumerate(pages):
        with cols[i]:
            t = "primary" if st.session_state.page==key else "secondary"
            if st.button(f"{label}", key=f"n{key}", use_container_width=True, type=t):
                st.session_state.page=key; st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    pg=st.session_state.page
    if pg=="overview":    pg_overview(products, source)
    elif pg=="topk":      pg_topk(products)
    elif pg=="analysis":  pg_ml(products)
    elif pg=="competitive": pg_competitive(products)
    elif pg=="infra":     pg_infra()

    st.markdown(f'''
    <div class="app-footer">
        Smart eCommerce Intelligence &nbsp;·&nbsp;
    </div>
    ''', unsafe_allow_html=True)

if __name__=="__main__": main()
run_dashboard=main