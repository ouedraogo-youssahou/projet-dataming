import logging
import json
import os
import asyncio
from typing import Any, Dict, List, Optional
from pathlib import Path

try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Smart eCommerce Intelligence", page_icon="📊", layout="wide")

# ─── Data Loading ───────────────────────────────────────────────

def load_products_from_db():
    try:
        import asyncpg
        host = os.getenv("POSTGRES_HOST", "postgres")
        user = os.getenv("POSTGRES_USER", "ecommerce_user")
        password = os.getenv("POSTGRES_PASSWORD", "secure_password")
        async def _fetch():
            conn = await asyncpg.connect(host=host, port=5432, database="ecommerce_db", user=user, password=password)
            rows = await conn.fetch("SELECT * FROM products ORDER BY price DESC")
            await conn.close()
            products = [dict(r) for r in rows]
            # Nettoyer les None pour éviter les erreurs Plotly
            for p in products:
                if p.get('reviews_count') is None:
                    p['reviews_count'] = 0
                if p.get('rating') is None:
                    p['rating'] = 0.0
                if p.get('price') is None:
                    p['price'] = 0.0
            return products
        return asyncio.run(_fetch())
    except Exception as e:
        logger.warning(f"PostgreSQL: {e}")
        return None

def load_products():
    db_products = load_products_from_db()
    if db_products and len(db_products) > 0:
        logger.info(f"Chargé {len(db_products)} produits depuis PostgreSQL")
        return db_products, "PostgreSQL"
    search_paths = [Path("data/raw/products.json"), Path("/app/data/raw/products.json")]
    for sp in search_paths:
        if sp.exists():
            try:
                with open(sp) as f:
                    data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    logger.info(f"Chargé {len(data)} produits depuis {sp}")
                    return data, sp.name
            except Exception:
                continue
    return [
        {"product_id": "1", "name": "Wireless Earbuds", "category": "Electronics", "price": 59.0, "rating": 4.6, "reviews_count": 1200, "availability": True},
        {"product_id": "2", "name": "Fitness Tracker", "category": "Sport", "price": 49.0, "rating": 4.2, "reviews_count": 340, "availability": True},
        {"product_id": "3", "name": "LED Desk Lamp", "category": "Home", "price": 29.0, "rating": 4.8, "reviews_count": 980, "availability": True},
    ], "sample"

def load_summary():
    for sp in [Path("data/processed/summary.txt"), Path("/app/data/processed/summary.txt")]:
        if sp.exists():
            try:
                return sp.read_text().strip()
            except IOError:
                continue
    return None

def compute_top_k(products: List[Dict], k: int = 10, weights: Optional[Dict] = None):
    w = weights or {"rating": 0.3, "reviews_count": 0.25, "price_competitiveness": 0.2, "availability": 0.15}
    df = pd.DataFrame(products)
    if df.empty:
        return pd.DataFrame()
    # Convert Decimal columns to float for numeric operations
    numeric_cols = ['price', 'rating', 'reviews_count', 'availability']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].astype(float)
    mp = df['price'].max() or 1
    mr = df['rating'].max() or 5
    mv = df['reviews_count'].max() or 1
    df['_score'] = (w["rating"] * (df['rating']/mr) + w["reviews_count"] * (df['reviews_count']/mv) +
                    w["price_competitiveness"] * (1-df['price']/mp) + w["availability"] * df['availability'])
    return df.sort_values('_score', ascending=False).head(k)

# ─── LLM Chatbot ────────────────────────────────────────────────

@st.cache_resource
def get_llm_wrapper():
    """Créer et mettre en cache le LLM wrapper avec les clés API depuis l'environnement."""
    import os
    from src.llm.wrapper import LLMWrapper
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    return LLMWrapper(deepseek_key=deepseek_key, groq_key=groq_key)

def ask_llm(prompt: str, products: Optional[List[Dict]] = None) -> str:
    """
    Appelle le LLM via LLMWrapper en utilisant uniquement Groq.
    Les produits sont inclus comme contexte pour des réponses précises.
    """
    llm = get_llm_wrapper()

    # Construire un contexte détaillé avec les produits
    if products and len(products) > 0:
        # Limiter à 50 produits pour ne pas dépasser le contexte LLM
        sample = products[:50]
        product_lines = []
        for p in sample:
            name = p.get('name', '?')
            price = p.get('price', 0)
            category = p.get('category', '?')
            rating = p.get('rating', 'N/A')
            avail = "✓" if p.get('availability') else "✗"
            product_lines.append(f"- {name} | {price:.0f}$ | {category} | {rating}/5 | {avail}")

        context = (
            "Tu es un assistant eCommerce expert. Voici les données produits disponibles :\n"
            f"Total : {len(products)} produits\n\n"
            "Liste des produits (nom | prix | catégorie | note | dispo):\n"
            + "\n".join(product_lines)
            + "\n\n"
            "Instructions :\n"
            "• Réponds précisément aux questions sur ces produits.\n"
            "• Si on te demande les produits les plus chers/moins chers, liste-les avec leurs détails.\n"
            "• Si on te demande des totaux, calcule-les.\n"
            "• Sois concis mais informatif."
        )
        full_prompt = context + f"\n\nQuestion : {prompt}"
    else:
        full_prompt = f"Tu es un assistant eCommerce. Réponds à : {prompt}"

    try:
        response = llm.complete(full_prompt, provider="groq", max_tokens=800)
        return response
    except RuntimeError as e:
        if "No LLM provider configured" in str(e):
            return "⚠️ Aucune clé API LLM configurée. Ajoutez GROQ_API_KEY dans le fichier .env"
        raise
    except Exception as e:
        return f"⚠️ Erreur LLM (Groq) : {str(e)}"

# ─── Render functions ───────────────────────────────────────────

def render_header():
    st.title("📊 Smart eCommerce Intelligence Dashboard")
    st.markdown("Données scrapées depuis WooCommerce, stockées dans PostgreSQL, analysées via Kubeflow, enrichies par LLM.")

def render_kpis(df_all, df_top):
    st.subheader("Indicateurs Clés")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total produits", len(df_all))
    c2.metric("Top-K affichés", len(df_top))
    c3.metric("Prix moyen", f"{df_all['price'].mean():.0f} $")
    c4.metric("Note moyenne", f"{df_all['rating'].mean():.2f} ⭐")

def render_filters(df):
    st.sidebar.header("Filtres")
    cats = ["Tous"] + sorted(df['category'].dropna().unique().tolist())
    cat = st.sidebar.selectbox("Catégorie", cats)
    k = st.sidebar.slider("Top-K", 1, min(20, len(df)), 10)
    pr = st.sidebar.slider("Prix max (USD)", 0, int(df['price'].max()), int(df['price'].max()))
    return cat, k, (0, pr)

def render_llm_summary(text):
    if text:
        st.subheader("🤖 Résumé LLM (DeepSeek)")
        st.info(text)

def render_top_k_table(df_top):
    st.subheader("🏆 Top-K Produits")
    cols = ["name", "category", "price", "rating", "reviews_count", "availability", "_score"]
    cols = [c for c in cols if c in df_top.columns]
    d = df_top[cols].copy().rename(columns={
        "name":"Produit","category":"Catégorie","price":"Prix ($)","rating":"Note",
        "reviews_count":"Avis","availability":"Dispo","_score":"Score"})
    st.dataframe(d, use_container_width=True)

def render_charts(df_all, df_top):
    st.subheader("📈 Visualisations & Storytelling")
    t1, t2, t3, t4 = st.tabs(["📊 Distribution", "🧩 Catégories", "🔬 Clusters", "📉 Storytelling"])

    with t1:
        fig = px.scatter(df_all, x='price', y='rating', color='category',
            size='reviews_count', hover_name='name', title="Prix vs Note")
        st.plotly_chart(fig, use_container_width=True)

    with t2:
        cc = df_all['category'].value_counts().reset_index()
        cc.columns = ['category','count']
        fig = px.pie(cc, values='count', names='category', title="Répartition catégories")
        st.plotly_chart(fig, use_container_width=True)

    with t3:
        from sklearn.preprocessing import StandardScaler
        import base64, io, joblib
        
        X = df_all[['price','rating','reviews_count']].fillna(0).values
        Xs = StandardScaler().fit_transform(X)
        
        # Essayer de charger les modèles depuis PostgreSQL
        models = {}
        for model_name in ['kmeans', 'dbscan', 'random_forest']:
            try:
                import asyncpg
                host = os.getenv("POSTGRES_HOST", "postgres")
                user = os.getenv("POSTGRES_USER", "ecommerce_user")
                password = os.getenv("POSTGRES_PASSWORD", "secure_password")
                async def load_model(name=model_name):
                    conn = await asyncpg.connect(host=host, port=5432, database="ecommerce_db", user=user, password=password)
                    row = await conn.fetchrow("SELECT model_data FROM kfp_models WHERE model_name=$1 ORDER BY created_at DESC LIMIT 1", name)
                    await conn.close()
                    if row:
                        b64 = row['model_data']
                        return joblib.load(io.BytesIO(base64.b64decode(b64)))
                    return None
                models[model_name] = asyncio.run(load_model())
            except Exception:
                pass
        
        # Sélection du modèle à afficher
        model_choice = st.radio("Modèle de clustering", ["KMeans", "DBSCAN", "RandomForest"], horizontal=True, key="model_choice")
        
        # Afficher les métriques si disponibles
        metrics = None
        try:
            import asyncpg, json as json_module
            async def load_metrics():
                conn = await asyncpg.connect(host=os.getenv("POSTGRES_HOST", "postgres"), port=5432, database="ecommerce_db", user=os.getenv("POSTGRES_USER", "ecommerce_user"), password=os.getenv("POSTGRES_PASSWORD", "secure_password"))
                row = await conn.fetchrow("SELECT metrics FROM model_metrics WHERE source='kubeflow_pipeline' ORDER BY created_at DESC LIMIT 1")
                await conn.close()
                if row:
                    m = row['metrics']
                    if isinstance(m, str):
                        return json_module.loads(m)
                    return m
                return None
            metrics = asyncio.run(load_metrics())
            if metrics:
                st.markdown(f"**📊 Métriques ML** — Silhouette: `{metrics.get('kmeans_silhouette', 'N/A')}` | DBSCAN Noise: `{metrics.get('dbscan_noise', 'N/A')}` | RF Accuracy: `{metrics.get('rf_accuracy', 'N/A')}`")
        except Exception:
            pass
        
        if model_choice == "KMeans" and models.get('kmeans'):
            model = models['kmeans']
            n = model.n_clusters
            df_all['_cluster'] = model.predict(Xs)
            st.caption(f"✅ Modèle KMeans chargé depuis PostgreSQL (K={n})")
            fig = px.scatter(df_all, x='price', y='rating', color='_cluster', hover_name='name', title=f"Clusters KMeans (K={n})")
            st.plotly_chart(fig, use_container_width=True)
            
        elif model_choice == "DBSCAN" and models.get('dbscan'):
            model = models['dbscan']
            labels = model.fit_predict(Xs)
            df_all['_cluster'] = labels
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            st.caption(f"✅ Modèle DBSCAN chargé depuis PostgreSQL (Clusters: {n_clusters}, Noise points: {(labels == -1).sum()})")
            fig = px.scatter(df_all, x='price', y='rating', color='_cluster', hover_name='name', title=f"Clusters DBSCAN ({n_clusters} clusters, {(labels == -1).sum()} bruit)")
            st.plotly_chart(fig, use_container_width=True)
            
        elif model_choice == "RandomForest" and models.get('random_forest'):
            model = models['random_forest']
            df_all['_cluster'] = model.predict(Xs)
            acc = metrics.get('rf_accuracy', 'N/A') if metrics else 'N/A'
            st.caption(f"✅ Modèle RandomForest chargé depuis PostgreSQL (Accuracy: {acc})")
            fig = px.scatter(df_all, x='price', y='rating', color='_cluster', hover_name='name', title="Classification RandomForest (Prix élevé/bas)")
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            # Fallback: entraîner à la volée
            from sklearn.cluster import KMeans, DBSCAN
            from sklearn.ensemble import RandomForestClassifier
            import numpy as np
            if model_choice == "KMeans":
                n = min(4, len(df_all))
                df_all['_cluster'] = KMeans(n_clusters=n, random_state=42, n_init=10).fit_predict(Xs)
                st.caption(f"⚡ KMeans entraîné à la volée (K={n})")
            elif model_choice == "DBSCAN":
                labels = DBSCAN(eps=0.5, min_samples=5).fit_predict(Xs)
                df_all['_cluster'] = labels
                st.caption(f"⚡ DBSCAN entraîné à la volée")
            else:
                y_binary = (X[:, 0] > np.median(X[:, 0])).astype(int)
                df_all['_cluster'] = RandomForestClassifier(n_estimators=50, random_state=42).fit(Xs, y_binary).predict(Xs)
                st.caption(f"⚡ RandomForest entraîné à la volée")
            
            fig = px.scatter(df_all, x='price', y='rating', color='_cluster', hover_name='name', title=f"{model_choice} (entraîné à la volée)")
            st.plotly_chart(fig, use_container_width=True)

    with t4:
        # Storytelling : insights automatiques sur les données
        st.markdown("#### 📖 Analyse des tendances produits")
        col1, col2 = st.columns(2)

        with col1:
            # Distribution des prix par catégorie (boxplot)
            fig = px.box(df_all, x='category', y='price', title="Distribution des prix par catégorie",
                color='category')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Top catégories par prix moyen
            avg_price = df_all.groupby('category')['price'].mean().sort_values(ascending=False).reset_index()
            fig = px.bar(avg_price, x='category', y='price', title="Prix moyen par catégorie",
                color='category', text_auto='.0f')
            st.plotly_chart(fig, use_container_width=True)

        # Insights textuels
        st.markdown("#### 💡 Insights")
        total = len(df_all)
        avg_p = df_all['price'].mean()
        max_p = df_all['price'].max()
        min_p = df_all['price'].min()
        top_cat = df_all['category'].value_counts().idxmax()
        top_cat_count = df_all['category'].value_counts().max()
        avg_r = df_all['rating'].mean()
        stock_pct = (df_all['availability'].sum() / total * 100) if total > 0 else 0

        insights = []
        if total > 0:
            insights.append(f"📦 **{total} produits** analysés dans **{df_all['category'].nunique()} catégories**.")
            insights.append(f"💰 Gamme de prix : **${min_p:.0f}** à **${max_p:.0f}** (moy. **${avg_p:.0f}**).")
            insights.append(f"🏷️ La catégorie **{top_cat}** domine avec **{top_cat_count} produits** ({top_cat_count/total*100:.0f}% du catalogue).")
            if stock_pct > 50:
                insights.append(f"✅ **{stock_pct:.0f}% des produits** sont en stock — bonne disponibilité.")
            else:
                insights.append(f"⚠️ Seulement **{stock_pct:.0f}%** des produits sont disponibles.")
            insights.append(f"⭐ Note moyenne : **{avg_r:.2f}/5**.")

        for ins in insights:
            st.markdown(ins)

def render_chatbot(products: List[Dict[str, Any]]):
    st.subheader("💬 Assistant IA (Groq)")
    st.markdown("Posez une question sur les produits. Le chatbot a accès à la base de données complète.")

    # Initialiser l'historique du chat
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Afficher l'historique
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Zone de saisie
    if prompt := st.chat_input("Ex: Quels sont les 5 produits les plus chers ?"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🧠 Réflexion..."):
                response = ask_llm(prompt, products=products)
            st.markdown(response)
        st.session_state.chat_history.append({"role": "assistant", "content": response})


def render_mcp_section():
    st.subheader("📡 MCP Server")
    st.markdown("`/tools/scrape_shopify` `/tools/scrape_woocommerce` `/tools/analyze_top_k` `/tools/generate_summary`")

# ─── Main ───────────────────────────────────────────────────────

def main():
    render_header()
    products, source = load_products()
    df_all = pd.DataFrame(products)
    summary = load_summary()
    render_llm_summary(summary)

    # Chatbot en sidebar (avec accès aux données produits)
    with st.sidebar:
        render_chatbot(products)

    # Filtres
    selected_cat, k, price_range = render_filters(df_all)
    mask = (df_all['price'] >= price_range[0]) & (df_all['price'] <= price_range[1])
    if selected_cat != "Tous":
        mask &= (df_all['category'] == selected_cat)
    df_filtered = df_all[mask].copy()

    df_top = compute_top_k(df_filtered.to_dict('records'), k=k)
    render_kpis(df_all, df_top)

    if not df_top.empty:
        render_top_k_table(df_top)
    else:
        st.warning("Aucun produit ne correspond aux filtres.")

    render_charts(df_filtered, df_top)
    render_mcp_section()
    st.caption(f"Smart eCommerce Intelligence — {len(products)} produits · Source : {source}")

if __name__ == "__main__":
    main()
run_dashboard = main