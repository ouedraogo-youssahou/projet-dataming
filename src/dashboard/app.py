"""
Smart eCommerce Intelligence
Design ultra-minimal, tout blanc, clean.
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
st.set_page_config(page_title="Smart eCommerce", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300..700&display=swap');
    * { font-family: 'Inter', sans-serif; box-sizing: border-box; }
    .stApp { background: #fff; }
    .main .block-container { padding: 0.5rem 1rem !important; max-width: 900px !important; }
    
    /* Header */
    .hdr { display: flex; align-items: center; justify-content: space-between; padding: 0.5rem 0; margin-bottom: 0.75rem; }
    .hdr h1 { font-size: 1rem; font-weight: 600; color: #222; margin: 0; }
    .hdr .tag { font-size: 0.7rem; color: #999; }
    .hdr .tag.g { color: #2E7D32; }
    
    /* Navigation pills */
    .pill { display: flex; gap: 0.2rem; padding: 2px; background: #f5f5f5; border-radius: 8px; margin-bottom: 1rem; }
    .pill button { flex: 1; text-align: center; padding: 0.35rem 0; font-size: 0.8rem; font-weight: 500; color: #aaa; border-radius: 7px; border: none; background: transparent; cursor: pointer; transition: all 0.12s; }
    .pill button:hover { color: #555; }
    .pill button.on { background: #fff; color: #111; box-shadow: 0 1px 2px rgba(0,0,0,0.04); font-weight: 600; }
    
    /* Titles */
    .pg { font-size: 1.1rem; font-weight: 700; color: #111; margin: 0 0 0.05rem; }
    .pg-s { color: #bbb; font-size: 0.8rem; margin-bottom: 1rem; }
    
    /* Stats grid */
    .gr { display: grid; grid-template-columns: repeat(4,1fr); gap: 0.5rem; margin-bottom: 0.75rem; }
    .bx { background: #fafafa; border: 1px solid #eee; border-radius: 8px; padding: 0.7rem 0.85rem; }
    .bx-l { color: #bbb; font-size: 0.62rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
    .bx-v { color: #111; font-size: 1.15rem; font-weight: 700; letter-spacing: -0.02em; margin: 1px 0; }
    .bx-f { color: #ccc; font-size: 0.65rem; }
    
    /* Cards */
    .cd { background: #fff; border: 1px solid #eee; border-radius: 10px; padding: 0.9rem 1rem; margin-bottom: 0.6rem; }
    .cd-l { color: #bbb; font-size: 0.62rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.1rem; }
    .cd-h { font-size: 0.78rem; font-weight: 600; color: #555; margin-bottom: 0.35rem; padding-bottom: 0.35rem; border-bottom: 1px solid #f5f5f5; display: flex; align-items: center; gap: 0.3rem; }
    
    .pb { background: #f0f0f0; border-radius: 20px; height: 3px; overflow: hidden; margin: 3px 0; }
    .pf { height: 100%; border-radius: 20px; background: #333; transition: width .4s; }
    
    /* Buttons */
    .stButton button { border-radius: 8px !important; font-weight: 500 !important; font-size: 0.8rem !important; border: none !important; padding: 0.2rem 0.75rem !important; background: #222 !important; color: #fff !important; transition: all .12s !important; }
    .stButton button:hover { background: #444 !important; }
    .stButton button[kind="secondary"] { background: #f5f5f5 !important; color: #444 !important; }
    .stButton button[kind="secondary"]:hover { background: #eee !important; }
    
    /* Table */
    div[data-testid="stDataFrame"] thead tr th { background: #fafafa !important; color: #bbb !important; font-weight: 600 !important; font-size: 0.65rem !important; text-transform: uppercase; border-bottom: 1px solid #eee !important; padding: 0.3rem 0.6rem !important; }
    div[data-testid="stDataFrame"] tbody tr td { color: #333 !important; font-size: 0.78rem !important; border-bottom: 1px solid #f5f5f5 !important; padding: 0.2rem 0.6rem !important; }
    div[data-testid="stDataFrame"] tbody tr:hover { background: #fafafa !important; }
    
    /* Tabs */
    div[data-testid="stTabs"] button { color: #ccc !important; font-weight: 500 !important; font-size: 0.78rem !important; padding: 0.15rem 0.65rem !important; border-bottom: 2px solid transparent !important; }
    div[data-testid="stTabs"] button[aria-selected="true"] { color: #111 !important; border-bottom: 2px solid #111 !important; }
    
    /* Chat */
    div[data-testid="chatMessage"] { background: #f8f8f8 !important; border: 1px solid #eee; border-radius: 8px !important; padding: 0.3rem 0.6rem !important; margin-bottom: 0.2rem; }
    div[data-testid="chatInput"] textarea { background: #f8f8f8 !important; border: 1px solid #eee !important; border-radius: 8px !important; color: #333 !important; font-size: 0.78rem !important; }
    
    div.stAlert { border-radius: 8px !important; border: 1px solid #eee !important; background: #fafafa !important; }
    div[data-testid="stExpander"] { border: 1px solid #eee !important; border-radius: 8px !important; margin-bottom: 0.35rem !important; background: #fff; }
    
    .ft { color: #ddd; font-size: 0.65rem; text-align: center; padding: 1rem 0 0.2rem; border-top: 1px solid #f0f0f0; margin-top: 1.25rem; }
    hr { border-color: #f0f0f0 !important; margin: 0.5rem 0 !important; }
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
            result = [_c(dict(x)) for x in r]
            return result
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
    # Toujours charger depuis PostgreSQL (pas de cache)
    db=load_products_from_db()
    if db and len(db)>0: return db,"PostgreSQL"
    for sp in [Path("data/raw/products.json"),Path("/app/data/raw/products.json")]:
        if sp.exists():
            try:
                with open(sp) as f: d=json.load(f)
                if isinstance(d,list) and len(d)>0: return d,sp.name
            except: pass
    return [{"product_id":"1","name":"Wireless Earbuds","category":"Electronics","price":59,"rating":4.6,"reviews_count":1200,"availability":True},{"product_id":"2","name":"Fitness Tracker","category":"Sport","price":49,"rating":4.2,"reviews_count":340,"availability":True},{"product_id":"3","name":"LED Desk Lamp","category":"Home","price":29,"rating":4.8,"reviews_count":980,"availability":True}],"Sample"

def topk(products,k=10,w=None):
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

def ask(prompt,products=None):
    w=llm()
    if products and len(products)>0:
        ctx=f"Assistant eCommerce. {len(products)} produits.\n"+'\n'.join([f"- {p.get('name','?')} | {p.get('price',0):.0f}$" for p in products[:50]])+f"\n\nQuestion: {prompt}"
    else: ctx=f"Réponds: {prompt}"
    try: return w.complete(ctx,provider="groq",max_tokens=800)
    except RuntimeError as e:
        if "No LLM provider" in str(e): return "⚠️ GROQ_API_KEY manquante"
        raise
    except: return "⚠️ Erreur"

# ─── PAGES ────────────────────────────────────────────────────

def pg_overview(products,src):
    st.markdown('<div class="pg">👋 Bonjour</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="pg-s">{len(products)} produits · {src}</div>',unsafe_allow_html=True)
    df=pd.DataFrame(products)
    for c in ['price','rating','reviews_count']:
        if c in df.columns: df[c]=pd.to_numeric(df[c],errors='coerce').fillna(0)
    ap=df['price'].mean(); ar=df['rating'].mean(); tr=int(df['reviews_count'].sum()); nc=df['category'].nunique() if 'category' in df.columns else 0
    av=(df['availability'].sum()/len(df)*100) if 'availability' in df.columns and len(df)>0 else 0
    st.markdown(f'<div class="gr"><div class="bx"><div class="bx-l">Produits</div><div class="bx-v">{len(df)}</div><div class="bx-f">{nc} catégories</div></div><div class="bx"><div class="bx-l">Prix moyen</div><div class="bx-v">{ap:.0f}$</div></div><div class="bx"><div class="bx-l">Note</div><div class="bx-v">{ar:.2f}</div></div><div class="bx"><div class="bx-l">Avis</div><div class="bx-v">{tr:,}</div></div></div>',unsafe_allow_html=True)
    if av>0: st.markdown(f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.75rem;"><span style="color:#bbb;font-size:0.7rem;">Disponibilité</span><div class="pb" style="flex:1;"><div class="pf" style="width:{av:.0f}%;"></div></div><span style="font-weight:600;font-size:0.78rem;">{av:.0f}%</span></div>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        fig=px.scatter(df,x='price',y='rating',color='category',size='reviews_count',hover_name='name',title="Prix / Note",color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',font_color='#bbb',title_font_color='#333',margin=dict(l=5,r=5,t=35,b=15),height=280)
        st.plotly_chart(fig,use_container_width=True)
    with c2:
        cc=df['category'].value_counts().reset_index(); cc.columns=['category','count']
        fig=px.pie(cc,values='count',names='category',title="Catégories",color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_traces(textposition='inside',textinfo='percent+label')
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',font_color='#bbb',title_font_color='#333',margin=dict(l=5,r=5,t=35,b=15),height=280)
        st.plotly_chart(fig,use_container_width=True)

def pg_topk(products):
    st.markdown('<div class="pg">🏷️ Top Produits</div>',unsafe_allow_html=True)
    st.markdown('<div class="pg-s">Classement par score.</div>',unsafe_allow_html=True)
    df=pd.DataFrame(products)
    for c in ['price','rating','reviews_count']:
        if c in df.columns: df[c]=pd.to_numeric(df[c],errors='coerce').fillna(0)
    cf,ct=st.columns([1,3])
    with cf:
        cats=["Tous"]+sorted(df['category'].dropna().unique().tolist())
        cat=st.selectbox("",cats,label_visibility="collapsed")
        k=st.slider("Top",1,min(20,len(df)),10)
        mx=int(df['price'].max()); pr=st.slider("Prix max",0,mx,mx)
    mask=(df['price']>=0)&(df['price']<=pr)
    if cat!="Tous": mask&=(df['category']==cat)
    df_top=topk(df[mask].to_dict('records'),k=k)
    if not df_top.empty:
        d=df_top[["name","category","price","rating","reviews_count","_s"]].copy().rename(columns={"name":"Produit","category":"Catégorie","price":"Prix ($)","rating":"Note","reviews_count":"Avis","_s":"Score"})
        st.dataframe(d,use_container_width=True,hide_index=True)
    else: st.warning("Aucun résultat.")

def pg_ml(products):
    st.markdown('<div class="pg">📈 Analyses</div>',unsafe_allow_html=True)
    st.markdown('<div class="pg-s">Clustering, prévisions, tendances.</div>',unsafe_allow_html=True)
    df=pd.DataFrame(products)
    for c in ['price','rating','reviews_count']:
        if c in df.columns: df[c]=pd.to_numeric(df[c],errors='coerce').fillna(0)
    from src.data_analysis import generate_trend_insights
    ti=generate_trend_insights(products)
    t1,t2,t3=st.tabs(["🔬 Clusters","🔮 Prévisions","🚀 Tendances"])
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
        mc=st.radio("",["PCA","KMeans","DBSCAN","RF"],horizontal=True,key="mc")
        if mc=="PCA":
            pca=PCA(n_components=2); Xp=pca.fit_transform(Xs); df['_x'],df['_y']=Xp[:,0],Xp[:,1]
            fig=px.scatter(df,x='_x',y='_y',color='category',hover_name='name',title=f"PCA ({pca.explained_variance_ratio_.sum()*100:.0f}%)",color_discrete_sequence=px.colors.qualitative.Set2).update_layout(plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',font_color='#bbb',title_font_color='#333')
            st.plotly_chart(fig,use_container_width=True)
        elif mc=="KMeans" and models.get('kmeans'):
            m=models['kmeans']; df['_cl']=m.predict(Xs).astype(str)
            fig=px.scatter(df,x='price',y='rating',color='_cl',hover_name='name',title=f"KMeans (K={m.n_clusters})",color_discrete_sequence=px.colors.qualitative.Set2).update_layout(plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',font_color='#bbb',title_font_color='#333')
            st.plotly_chart(fig,use_container_width=True)
        elif mc=="DBSCAN" and models.get('dbscan'):
            m=models['dbscan']; l=m.fit_predict(Xs); df['_cl']=l.astype(str)
            fig=px.scatter(df[l!=-1],x='price',y='rating',color='_cl',hover_name='name',title="DBSCAN",color_discrete_sequence=px.colors.qualitative.Set2).update_layout(plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',font_color='#bbb',title_font_color='#333')
            st.plotly_chart(fig,use_container_width=True)
        elif mc=="RF" and models.get('random_forest'):
            m=models['random_forest']; df['_cl']=m.predict(Xs).astype(str)
            fig=px.scatter(df,x='price',y='rating',color='_cl',hover_name='name',title="RF",color_discrete_sequence=px.colors.qualitative.Set2).update_layout(plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',font_color='#bbb',title_font_color='#333')
            st.plotly_chart(fig,use_container_width=True)
        else:
            from sklearn.cluster import KMeans,DBSCAN; from sklearn.ensemble import RandomForestClassifier
            if mc=="KMeans": l=KMeans(n_clusters=min(4,len(df)),random_state=42,n_init=10).fit_predict(Xs)
            elif mc=="DBSCAN": l=DBSCAN(eps=0.5,min_samples=5).fit_predict(Xs)
            else: l=RandomForestClassifier(n_estimators=50,random_state=42).fit(Xs,(X[:,0]>np.median(X[:,0])).astype(int)).predict(Xs)
            df['_cl']=l.astype(str)
            fig=px.scatter(df,x='price',y='rating',color='_cl',hover_name='name',title=mc,color_discrete_sequence=px.colors.qualitative.Set2).update_layout(plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',font_color='#bbb',title_font_color='#333')
            st.plotly_chart(fig,use_container_width=True)
    with t2:
        fc=ti.get('category_price_forecasts',{}); tr=ti.get('category_price_trends',{})
        if fc:
            cat=st.selectbox("",list(fc.keys()),key="pc",label_visibility="collapsed")
            c1,c2=st.columns([2,1])
            with c1:
                f=fc[cat]
                fig=go.Figure()
                fig.add_trace(go.Scatter(x=f['dates'],y=f['values'],mode='lines+markers',name='30j',line=dict(color='#333',width=2,dash='dash')))
                fig.add_trace(go.Scatter(x=f['dates']+f['dates'][::-1],y=f['upper']+f['lower'][::-1],fill='toself',fillcolor='rgba(0,0,0,0.04)',line=dict(color='rgba(0,0,0,0)'),hoverinfo="skip",name='IC'))
                fig.update_layout(title=f"{cat}",xaxis_title="Date",yaxis_title="Prix ($)",hovermode='x unified',plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',font_color='#bbb',title_font_color='#333',height=260)
                st.plotly_chart(fig,use_container_width=True)
            with c2:
                ci=tr.get(cat,{})
                if ci: st.markdown(f'<div class="cd"><div class="cd-l">Tendance</div><div style="font-size:0.95rem;font-weight:600;color:{"#2E7D32" if ci.get("trend")=="growing" else "#C62828" if ci.get("trend")=="declining" else "#E65100"};">{ci.get("trend","N/A")}</div><div style="margin-top:0.35rem;"><span class="cd-l">Moy.</span><div style="font-weight:600;">${ci.get("avg_price",0):.2f}</div></div></div>',unsafe_allow_html=True)
        else: st.info("≥5 produits/catégorie requis.")
    with t3:
        tr=ti.get('trending_products',[]); acc=ti.get('xgboost_accuracy')
        ca,cb=st.columns([1,2])
        with ca:
            if tr and len(products)>=30: st.metric("Accuracy",f"{acc:.1%}" if acc else "N/A"); st.success("✅ OK")
            elif len(products)>=30: st.info("Non disponible")
            else: st.warning(f"≥30 requis ({len(products)})")
        with cb:
            if tr:
                for i,p in enumerate(tr[:5],1): st.markdown(f"**{i}.** {p['name']} — `{p['score']:.3f}`")
            else: st.info("Aucun")
        if tr:
            sdf=pd.DataFrame(tr[:8])
            fig=px.bar(sdf,x='name',y='score',color='score',color_continuous_scale='Oranges',labels={'name':'','score':''})
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',font_color='#bbb',height=160,margin=dict(l=5,r=5,t=5,b=25))
            st.plotly_chart(fig,use_container_width=True)

def pg_competitive(products):
    st.markdown('<div class="pg">🏆 Concurrence</div>',unsafe_allow_html=True)
    st.markdown('<div class="pg-s">Analyses Groq.</div>',unsafe_allow_html=True)
    from src.llm.competitive_analysis import CompetitiveAnalysis
    gk=os.getenv("GROQ_API_KEY","")
    if not gk: st.warning("GROQ_API_KEY → .env"); return
    if not products or len(products)==0: st.info("Aucun produit."); return
    b1,b2,b3,_=st.columns([1,1,1,1.5])
    with b1: r1=st.button("🔍 Comparer",type="primary",use_container_width=True,key="c1")
    with b2: r2=st.button("📈 Émergents",use_container_width=True,key="c2")
    with b3: r3=st.button("🎯 Stratégie",use_container_width=True,key="c3")
    if "cr" not in st.session_state: st.session_state.cr={}
    try:
        an=CompetitiveAnalysis(groq_key=gk)
        if r1 or st.session_state.get("cs1"):
            st.session_state.cs1=True
            if "cmp" not in st.session_state.cr:
                with st.spinner("Groq..."): st.session_state.cr["cmp"]=an.compare_products(products)
            res=st.session_state.cr["cmp"]
            if res.get("status")=="completed":
                for comp in res.get("comparisons",[]):
                    with st.expander(f"📦 {comp['category']} ({comp['products_compared']})",expanded=True):
                        ca,cb=st.columns([1,2])
                        with ca: st.markdown(f'<div class="cd"><div class="cd-l">Prix moy.</div><div style="font-size:1rem;font-weight:700;">${comp["price_range"]["avg"]:.0f}</div><div class="cd-l" style="margin-top:0.35rem;">Note</div><div style="font-size:1rem;font-weight:700;">{comp["avg_rating"]:.2f}/5</div></div>',unsafe_allow_html=True)
                        with cb: st.markdown(f'<div class="cd">{comp.get("analysis_text","")}</div>',unsafe_allow_html=True)
            else: st.info(res.get("message",""))
        if r2 or st.session_state.get("cs2"):
            st.session_state.cs2=True
            if "emg" not in st.session_state.cr:
                with st.spinner("Groq..."): st.session_state.cr["emg"]=an.generate_emerging_report(products)
            res=st.session_state.cr["emg"]
            if res.get("status")=="completed":
                el=res.get("emerging_products",[])
                if el:
                    edf=pd.DataFrame(el)
                    cols=[c for c in ["rank","name","category","price","rating","reviews_count","emergence_score"] if c in edf.columns]
                    disp=edf[cols].rename(columns={"rank":"#","name":"Produit","category":"Catégorie","price":"Prix ($)","rating":"Note","reviews_count":"Avis","emergence_score":"Score"})
                    st.dataframe(disp,use_container_width=True,hide_index=True)
                    fig=px.bar(edf,x='name',y='emergence_score',color='emergence_score',color_continuous_scale='Greens',labels={'name':'','emergence_score':''})
                    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',font_color='#bbb',height=160,margin=dict(l=5,r=5,t=5,b=25))
                    st.plotly_chart(fig,use_container_width=True)
                rt=res.get("report_text","")
                if rt: st.markdown(f'<div class="cd">{rt}</div>',unsafe_allow_html=True)
            else: st.info(res.get("message",""))
        if r3 or st.session_state.get("cs3"):
            st.session_state.cs3=True
            if "rec" not in st.session_state.cr:
                with st.spinner("Groq..."): st.session_state.cr["rec"]=an.generate_strategic_recommendations(products)
            res=st.session_state.cr["rec"]
            if res.get("status")=="completed":
                segs=res.get("segments",[])
                if segs:
                    for s in segs[:5]:
                        st.markdown(f'<div style="background:#f8f8f8;border:1px solid #eee;border-radius:8px;padding:0.35rem 0.65rem;margin-bottom:0.2rem;"><div style="display:flex;justify-content:space-between;"><span style="font-weight:600;">{s["category"]}</span><span style="color:#bbb;">{s["value_score"]:.3f}</span></div><div style="color:#aaa;font-size:0.68rem;">{s["product_count"]} produits · ${s["avg_price"]:.0f} · {s["avg_rating"]}/5</div></div>',unsafe_allow_html=True)
                rt=res.get("recommendations_text","")
                if rt: st.markdown(f'<div class="cd">{rt}</div>',unsafe_allow_html=True)
            else: st.info(res.get("message",""))
    except Exception as e: st.error(f"❌ {str(e)}"); logger.error(f"CA: {e}",exc_info=True)

def pg_infra():
    st.markdown('<div class="pg">⚙️ Infrastructure</div>',unsafe_allow_html=True)
    st.markdown('<div class="pg-s">Pipeline & Services.</div>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        st.markdown('<div class="cd"><div class="cd-h">🚀 Pipeline</div>',unsafe_allow_html=True)
        if st.button("▶️ Lancer",type="primary",use_container_width=True):
            with st.spinner("..."):
                try:
                    import subprocess
                    h=os.getenv("KFP_HOST","http://host.docker.internal:61567")
                    r=subprocess.run(["python","scripts/run_kfp.py","--host",h],capture_output=True,text=True,timeout=120,cwd="/app")
                    if r.returncode==0: st.success("✅ OK"); st.code(r.stdout[-150:] if len(r.stdout)>150 else r.stdout)
                    else: st.error(f"❌ {r.stderr[-150:]}")
                except subprocess.TimeoutExpired: st.warning("⏳ Timeout")
                except Exception as e: st.error(f"❌ {str(e)}")
        st.markdown('<div style="color:#bbb;font-size:0.7rem;margin-top:0.35rem;">Scraping → Prep → ML → DB</div></div>',unsafe_allow_html=True)
    with c2:
        eps=[("GET /health","Health"),("/tools/scrape_shopify","Shopify"),("/tools/scrape_woocommerce","Woo"),("/tools/analyze_top_k","Top-K"),("/tools/competitive_analysis","Concurrence")]
        h='<div class="cd"><div class="cd-h">📡 MCP (8000)</div>'
        for e,d in eps: h+=f'<div style="display:flex;justify-content:space-between;padding:0.12rem 0;border-bottom:1px solid #f5f5f5;font-size:0.76rem;"><span style="color:#666;font-family:monospace;">{e}</span><span style="color:#bbb;">{d}</span></div>'
        h+='</div>'; st.markdown(h,unsafe_allow_html=True)

# ─── MAIN ─────────────────────────────────────────────────────

def main():
    if "page" not in st.session_state: st.session_state.page="overview"
    # Force reload products every time to avoid stale data
    p, s = load_products()
    st.session_state.pc = p
    st.session_state.sc = s
    products = p
    source = s
    
    # Ensure products is always a valid list of dicts
    if not isinstance(products, list) or len(products) == 0:
        products = []
        st.warning("Aucune donnée produit disponible.")
    
    # ── SIDEBAR : Chat toujours visible à gauche ──
    with st.sidebar:
        st.markdown("## 💬 Assistant IA")
        st.markdown("Posez une question sur les produits.")
        st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)
        
        if "ch" not in st.session_state: st.session_state.ch=[]
        # Afficher l'historique (limit 6 messages)
        for msg in st.session_state.ch[-6:]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        # Zone de saisie en bas de la sidebar
        if pr := st.chat_input("Question sur les produits..."):
            st.session_state.ch.append({"role":"user","content":pr})
            with st.chat_message("user"):
                st.markdown(pr)
            with st.chat_message("assistant"):
                with st.spinner(""):
                    r = ask(pr, products)
                st.markdown(r)
            st.session_state.ch.append({"role":"assistant","content":r})
    
    # ── MAIN CONTENT ──
    cls = "tag" + (" g" if source=="PostgreSQL" else "")
    st.markdown(f'<div class="hdr"><h1>📊 Smart eCommerce</h1><span class="{cls}">{len(products)} produits</span></div>',unsafe_allow_html=True)
    
    pages=[("📊","Vue d\'ensemble","overview"),("🏷️","Top","topk"),("📈","Analyses","analysis"),("🏆","Concurrence","competitive"),("⚙️","Infra","infra")]
    nav='<div class="pill">'
    for _,label,key in pages:
        nav+=f'<button class="{"on" if st.session_state.page==key else ""}" onclick="alert(\'{key}\')">{label}</button>'
    nav+='</div>'
    st.markdown(nav,unsafe_allow_html=True)
    
    cols=st.columns(len(pages))
    for i,(_,label,key) in enumerate(pages):
        with cols[i]:
            if st.button(label,key=f"n{key}",use_container_width=True,type="secondary" if st.session_state.page!=key else "primary"): st.session_state.page=key; st.rerun()
    
    st.markdown("<hr>",unsafe_allow_html=True)
    
    p=st.session_state.page
    if p=="overview": pg_overview(products,source)
    elif p=="topk": pg_topk(products)
    elif p=="analysis": pg_ml(products)
    elif p=="competitive": pg_competitive(products)
    elif p=="infra": pg_infra()
    
    st.markdown(f'<div class="ft">Smart eCommerce · {len(products)} produits · {source}</div>',unsafe_allow_html=True)

if __name__=="__main__": main()
run_dashboard=main