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
    """Returns a simple emoji span instead of SVG — zero rendering issues."""
    icons = {
        "bar-chart":      "📊",
        "tag":            "🏷️",
        "trending-up":    "📈",
        "award":          "🏆",
        "settings":       "⚙️",
        "message-square": "💬",
        "package":        "📦",
        "dollar-sign":    "💰",
        "star":           "⭐",
        "users":          "👥",
        "grid":           "▦",
        "check-circle":   "✅",
        "play":           "▶️",
        "activity":       "⚡",
        "search":         "🔍",
        "send":           "📨",
        "cpu":            "🖥️",
        "wifi":           "🌐",
        "arrow-up":       "↑",
        "arrow-down":     "↓",
        "minus":          "—",
        "layers":         "🗂️",
        "compass":        "🧭",
    }
    emoji = icons.get(name, "•")
    return f'<span class="icon-emoji {cls}" style="font-size:{size}px;line-height:1;">{emoji}</span>'

CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&family=DM+Mono:wght@400;500&display=swap');

    :root {
        --bg:        #F0F4FF;
        --surface:   #FFFFFF;
        --border:    #D6E0FF;
        --border-md: #B8C8FF;
        --ink-0:     #1E1B4B;
        --ink-1:     #3730A3;
        --ink-2:     #6366F1;
        --ink-3:     #A5B4FC;
        --ink-4:     #C7D2FE;
        --accent:    #6366F1;
        --accent-lt: #EEF2FF;
        --green:     #059669;
        --green-lt:  #D1FAE5;
        --red:       #DC2626;
        --red-lt:    #FEE2E2;
        --yellow:    #D97706;
        --yellow-lt: #FEF3C7;
        --pink:      #DB2777;
        --pink-lt:   #FCE7F3;
        --shadow-sm: 0 1px 3px rgba(99,102,241,0.10), 0 1px 2px rgba(99,102,241,0.06);
        --shadow-md: 0 4px 12px rgba(99,102,241,0.12), 0 2px 4px rgba(99,102,241,0.06);
        --r-sm: 8px;
        --r-md: 12px;
        --r-lg: 16px;
    }

    * { font-family: 'DM Sans', sans-serif; box-sizing: border-box; }
    code, pre, .mono { font-family: 'DM Mono', monospace; }

    /* ── App shell ── */
    .stApp { background: var(--bg) !important; }
    section[data-testid="stSidebar"] { background: var(--surface) !important; border-right: 2px solid var(--border) !important; }
    .main .block-container { padding: 0 1.5rem 2rem !important; max-width: 980px !important; }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] .block-container { padding: 1.25rem 1rem !important; }
    .sidebar-logo {
        display: flex; align-items: center; gap: 0.5rem;
        padding: 0 0 1rem; margin-bottom: 1rem;
        border-bottom: 2px solid var(--border);
    }
    .sidebar-logo .mark {
        width: 32px; height: 32px;
        background: linear-gradient(135deg, #6366F1, #8B5CF6);
        border-radius: 8px; display: flex; align-items: center; justify-content: center;
        flex-shrink: 0; font-size: 16px;
    }
    .sidebar-logo h2 { font-size: 0.85rem; font-weight: 700; color: var(--ink-0); margin: 0; letter-spacing: -0.01em; }
    .sidebar-logo span { font-size: 0.7rem; color: var(--ink-3); display: block; font-weight: 400; }

    .sidebar-section {
        font-size: 0.65rem; font-weight: 700; color: var(--ink-2);
        text-transform: uppercase; letter-spacing: 0.08em;
        margin: 1.25rem 0 0.6rem;
    }

    /* Chat messages */
    div[data-testid="chatMessage"] {
        background: var(--accent-lt) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--r-md) !important;
        padding: 0.55rem 0.75rem !important;
        margin-bottom: 0.35rem;
        box-shadow: none !important;
    }
    div[data-testid="chatMessage"] p { font-size: 0.82rem !important; color: var(--ink-0) !important; line-height: 1.55 !important; }
    div[data-testid="stChatInput"] {
        background: var(--surface) !important;
        border: 2px solid var(--border-md) !important;
        border-radius: var(--r-md) !important;
    }
    div[data-testid="stChatInput"] textarea {
        background: transparent !important;
        color: var(--ink-0) !important;
        font-size: 0.82rem !important;
    }

    /* ── Top header ── */
    .app-header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 1.25rem 0 0.5rem;
        margin-bottom: 0.5rem;
    }
    .app-header .wordmark {
        display: flex; align-items: center; gap: 0.6rem;
    }
    .app-header .mark {
        width: 36px; height: 36px;
        background: linear-gradient(135deg, #6366F1, #8B5CF6);
        border-radius: var(--r-sm); display: flex; align-items: center; justify-content: center;
        font-size: 18px;
    }
    .app-header h1 { font-size: 1.1rem; font-weight: 700; color: var(--ink-0); margin: 0; letter-spacing: -0.02em; }
    .app-header .badge {
        font-size: 0.7rem; font-weight: 600; padding: 0.25rem 0.65rem;
        border-radius: 20px; border: 1px solid var(--border);
        color: var(--ink-2); background: var(--accent-lt);
    }
    .app-header .badge.live {
        color: var(--green); border-color: var(--green-lt);
        background: var(--green-lt);
    }

    /* ── Nav tabs ── */
    .stButton button {
        border-radius: var(--r-sm) !important;
        border: 2px solid var(--border) !important;
        background: var(--surface) !important;
        color: var(--ink-2) !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.15s ease !important;
    }
    .stButton button:hover {
        border-color: var(--accent) !important;
        color: var(--accent) !important;
        background: var(--accent-lt) !important;
    }
    .stButton button[kind="primary"] {
        color: #FFFFFF !important;
        background: linear-gradient(135deg, #6366F1, #8B5CF6) !important;
        border-color: transparent !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 8px rgba(99,102,241,0.35) !important;
    }
    .stButton button[kind="secondary"] {
        color: var(--ink-2) !important;
        background: var(--surface) !important;
        border-color: var(--border) !important;
    }

    /* ── Page title ── */
    .pg-title { font-size: 1.35rem; font-weight: 800; color: var(--ink-0); margin: 0 0 0.15rem; letter-spacing: -0.025em; }
    .pg-sub { color: var(--ink-3); font-size: 0.8rem; margin-bottom: 1.25rem; font-weight: 400; }

    /* ── Stat cards ── */
    .stats-grid {
        display: grid; grid-template-columns: repeat(4, 1fr);
        gap: 0.75rem; margin-bottom: 1rem;
    }
    .stat-card {
        background: var(--surface); border: 2px solid var(--border);
        border-radius: var(--r-lg); padding: 1rem 1.1rem;
        box-shadow: var(--shadow-sm); position: relative; overflow: hidden;
    }
    .stat-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0;
        height: 3px; background: var(--border-md);
    }
    .stat-card.accent::before { background: linear-gradient(90deg, #6366F1, #8B5CF6); }
    .stat-card.green::before  { background: var(--green); }
    .stat-card.yellow::before { background: var(--yellow); }
    .stat-card.pink::before   { background: var(--pink); }
    .stat-icon {
        width: 32px; height: 32px; border-radius: var(--r-sm);
        background: var(--accent-lt); border: 1px solid var(--border);
        display: flex; align-items: center; justify-content: center;
        margin-bottom: 0.6rem; font-size: 16px;
    }
    .stat-label { font-size: 0.65rem; font-weight: 700; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 0.1rem; }
    .stat-value { font-size: 1.5rem; font-weight: 800; color: var(--ink-0); letter-spacing: -0.03em; line-height: 1; }
    .stat-foot { font-size: 0.67rem; color: var(--ink-3); margin-top: 0.25rem; }

    /* ── Data cards ── */
    .data-card {
        background: var(--surface); border: 2px solid var(--border);
        border-radius: var(--r-md); padding: 1rem 1.1rem;
        margin-bottom: 0.65rem; box-shadow: var(--shadow-sm);
    }
    .data-card-label { font-size: 0.62rem; font-weight: 700; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 0.25rem; }
    .data-card-header {
        font-size: 0.78rem; font-weight: 700; color: var(--ink-1);
        margin-bottom: 0.5rem; padding-bottom: 0.45rem;
        border-bottom: 2px solid var(--border);
        display: flex; align-items: center; gap: 0.4rem;
    }

    /* ── Progress bar ── */
    .prog-wrap { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.9rem; }
    .prog-label { color: var(--ink-1); font-size: 0.75rem; white-space: nowrap; font-weight: 600; }
    .prog-track { flex: 1; background: var(--bg); border-radius: 20px; height: 6px; overflow: hidden; border: 1px solid var(--border); }
    .prog-fill { height: 100%; border-radius: 20px; background: linear-gradient(90deg, #6366F1, #8B5CF6); transition: width 0.5s ease; }
    .prog-val { font-weight: 700; font-size: 0.78rem; color: var(--accent); white-space: nowrap; }

    /* ── Table ── */
    div[data-testid="stDataFrame"] {
        border: 2px solid var(--border) !important;
        border-radius: var(--r-md) !important;
        overflow: hidden;
        box-shadow: var(--shadow-sm);
    }
    div[data-testid="stDataFrame"] thead tr th {
        background: var(--accent-lt) !important; color: var(--ink-1) !important;
        font-weight: 700 !important; font-size: 0.65rem !important;
        text-transform: uppercase; letter-spacing: 0.06em;
        border-bottom: 2px solid var(--border) !important;
        padding: 0.5rem 0.75rem !important;
    }
    div[data-testid="stDataFrame"] tbody tr td {
        color: var(--ink-0) !important; font-size: 0.82rem !important;
        border-bottom: 1px solid var(--border) !important;
        padding: 0.4rem 0.75rem !important;
        background: var(--surface) !important;
    }
    div[data-testid="stDataFrame"] tbody tr:hover td { background: var(--accent-lt) !important; }

    /* ── Expanders ── */
    div[data-testid="stExpander"] {
        border: 2px solid var(--border) !important;
        border-radius: var(--r-md) !important;
        margin-bottom: 0.5rem !important;
        background: var(--surface);
        box-shadow: var(--shadow-sm);
        overflow: hidden;
    }
    div[data-testid="stExpander"] summary {
        font-size: 0.84rem !important; font-weight: 700 !important;
        color: var(--ink-0) !important; padding: 0.65rem 0.85rem !important;
        background: var(--accent-lt) !important;
    }

    /* ── Tabs ── */
    div[data-testid="stTabs"] {
        border-bottom: 2px solid var(--border);
        margin-bottom: 1rem;
    }
    div[data-testid="stTabs"] button {
        color: var(--ink-3) !important; font-weight: 600 !important;
        font-size: 0.8rem !important;
        padding: 0.4rem 0.85rem !important;
        border-bottom: 2px solid transparent !important;
        border-radius: 0 !important;
        background: transparent !important;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--accent) !important;
        border-bottom-color: var(--accent) !important;
        font-weight: 700 !important;
    }

    /* ── Alerts ── */
    div.stAlert {
        border-radius: var(--r-md) !important;
        border: 2px solid var(--border) !important;
        background: var(--accent-lt) !important;
        font-size: 0.82rem !important;
    }

    /* ── Selects & sliders ── */
    div[data-testid="stSelectbox"] select, div[data-testid="stSelectbox"] > div > div {
        background: var(--surface) !important;
        border: 2px solid var(--border) !important;
        border-radius: var(--r-sm) !important;
        color: var(--ink-0) !important;
        font-size: 0.82rem !important;
    }
    div[data-testid="stSlider"] > div > div > div { background: var(--accent) !important; }

    /* ── Radio ── */
    div[data-testid="stRadio"] label { font-size: 0.82rem !important; color: var(--ink-0) !important; }

    /* ── HR ── */
    hr { border-color: var(--border) !important; margin: 0.75rem 0 !important; }

    /* ── Footer ── */
    .app-footer {
        color: var(--ink-3); font-size: 0.67rem; text-align: center;
        padding: 1.5rem 0 0.5rem; border-top: 2px solid var(--border);
        margin-top: 2rem; letter-spacing: 0.04em; text-transform: uppercase;
        font-weight: 600;
    }

    /* Inline icon alignment */
    .icon-emoji { display: inline-flex; align-items: center; vertical-align: middle; }
    .icon-inline { display: inline-flex; align-items: center; vertical-align: middle; }
    .with-icon { display: flex; align-items: center; gap: 0.4rem; }

    /* Trend badges */
    .trend-badge {
        display: inline-flex; align-items: center; gap: 0.25rem;
        font-size: 0.7rem; font-weight: 700; padding: 0.2rem 0.5rem;
        border-radius: 20px;
    }
    .trend-up   { color: var(--green); background: var(--green-lt); }
    .trend-down { color: var(--red);   background: var(--red-lt); }
    .trend-flat { color: var(--ink-2); background: var(--accent-lt); }

    /* Segment row */
    .seg-row {
        display: flex; align-items: center; justify-content: space-between;
        padding: 0.5rem 0.75rem; border-radius: var(--r-sm);
        background: var(--accent-lt); border: 2px solid var(--border);
        margin-bottom: 0.35rem;
    }
    .seg-name { font-weight: 700; font-size: 0.82rem; color: var(--ink-0); }
    .seg-meta { font-size: 0.7rem; color: var(--ink-3); margin-top: 0.05rem; }
    .seg-score { font-family: 'DM Mono', monospace; font-size: 0.78rem; color: var(--accent); font-weight: 700; }

    /* MCP endpoint rows */
    .ep-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.35rem 0; border-bottom: 1px solid var(--border);
        font-size: 0.78rem;
    }
    .ep-row:last-child { border-bottom: none; }
    .ep-path { font-family: 'DM Mono', monospace; color: var(--accent); font-size: 0.74rem; font-weight: 600; }
    .ep-desc { color: var(--ink-3); font-size: 0.72rem; }

    /* Pipeline status */
    .pipe-steps {
        display: flex; align-items: center; gap: 0; margin: 0.75rem 0;
    }
    .pipe-step {
        flex: 1; text-align: center; position: relative;
        font-size: 0.7rem; color: var(--ink-2); font-weight: 600;
    }
    .pipe-step-dot {
        width: 10px; height: 10px; border-radius: 50%;
        background: var(--border-md); margin: 0 auto 0.3rem; position: relative; z-index: 1;
    }
    .pipe-step-dot.done { background: linear-gradient(135deg, #6366F1, #8B5CF6); }
    .pipe-step::after {
        content: ''; position: absolute; top: 5px; left: 50%; right: -50%;
        height: 2px; background: var(--border-md); z-index: 0;
    }
    .pipe-step:last-child::after { display: none; }
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

        mc=st.radio("Algorithme", ["PCA","KMeans","DBSCAN","Random Forest"], horizontal=True, key="mc")

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
        elif mc=="Random Forest" and models.get('random_forest'):
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
        r1=st.button("🔍 Comparer", type="primary", use_container_width=True, key="c1")
    with b2:
        r2=st.button("📈 Émergents", use_container_width=True, key="c2")
    with b3:
        r3=st.button("🧭 Stratégie", use_container_width=True, key="c3")

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

        if st.button("▶️ Lancer le pipeline", type="primary", use_container_width=True):
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
        st.markdown(f'''
        <div class="sidebar-logo">
            <div class="mark">🗂️</div>
            <div>
                <h2>Smart eCommerce</h2>
                <span>Intelligence produit</span>
            </div>
        </div>
        ''', unsafe_allow_html=True)

        st.markdown(f'<div class="sidebar-section">💬 Assistant IA</div>', unsafe_allow_html=True)

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

    # ── HEADER ──
   
    st.markdown(f'''
    <div class="app-header">
        <div class="wordmark">
            <div class="mark">🗂️</div>
            <h1>Smart eCommerce</h1>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    # ── NAV ──
    pages = [
    (icon("bar-chart",13), "Vue d'ensemble", "overview"),
    (icon("tag",13), "Les Top-K produits", "topk"),
    (icon("trending-up",13), "Machine Learning", "analysis"),
    (icon("award",13), "Analyse concurentielle", "competitive"),
    (icon("settings",13), "Orchestration", "infra"),
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