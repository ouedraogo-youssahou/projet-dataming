import logging
import json
import os
import asyncio
from typing import Any, Dict, List, Optional

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

logger = logging.getLogger(__name__)

# Page config
st.set_page_config(page_title="Smart eCommerce Intelligence", page_icon="📊", layout="wide")


def load_products_from_db():
    """Charge les produits depuis PostgreSQL (connexion directe)."""
    try:
        import asyncpg
        host = os.getenv("POSTGRES_HOST", "postgres")
        user = os.getenv("POSTGRES_USER", "ecommerce_user")
        password = os.getenv("POSTGRES_PASSWORD", "secure_password")

        async def _fetch():
            conn = await asyncpg.connect(
                host=host, port=5432, database="ecommerce_db",
                user=user, password=password
            )
            rows = await conn.fetch(
                "SELECT product_id, name, description, category, price, currency, "
                "availability, quantity, rating, reviews_count, images, tags, vendor "
                "FROM products ORDER BY price DESC"
            )
            await conn.close()
            return [dict(r) for r in rows]

        return asyncio.run(_fetch())
    except Exception as e:
        logger.warning(f"Connexion PostgreSQL échouée: {e}")
        return None


def load_products():
    """Charge les produits : d'abord PostgreSQL, puis fallback JSON, puis sample data."""
    # Essayer PostgreSQL d'abord
    db_products = load_products_from_db()
    if db_products and len(db_products) > 0:
        logger.info(f"Chargé {len(db_products)} produits depuis PostgreSQL")
        return db_products, "PostgreSQL"

    # Fallback: fichier products.json
    search_paths = [
        Path("data/raw/products.json"),
        Path("/app/data/raw/products.json"),
    ]
    for sp in search_paths:
        if sp.exists():
            try:
                with open(sp) as f:
                    data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    logger.info(f"Chargé {len(data)} produits depuis {sp}")
                    return data, sp.name
            except (json.JSONDecodeError, IOError):
                continue

    # Fallback: données sample
    logger.warning("Aucune source trouvée, utilisation des données sample")
    return [
        {"product_id": "1", "name": "Wireless Earbuds", "category": "Electronics", "price": 59.0, "rating": 4.6, "reviews_count": 1200, "availability": True, "vendor": "TechStore"},
        {"product_id": "2", "name": "Fitness Tracker", "category": "Sport", "price": 49.0, "rating": 4.2, "reviews_count": 340, "availability": True, "vendor": "FitShop"},
        {"product_id": "3", "name": "LED Desk Lamp", "category": "Home", "price": 29.0, "rating": 4.8, "reviews_count": 980, "availability": True, "vendor": "BrightHome"},
        {"product_id": "4", "name": "Bluetooth Speaker", "category": "Electronics", "price": 79.0, "rating": 4.4, "reviews_count": 450, "availability": False, "vendor": "SoundCo"},
        {"product_id": "5", "name": "Yoga Mat", "category": "Sport", "price": 25.0, "rating": 4.7, "reviews_count": 2100, "availability": True, "vendor": "FitShop"},
    ], "données de démonstration"


def load_summary():
    """Charge le résumé LLM généré par Kubeflow."""
    search_paths = [
        Path("data/processed/summary.txt"),
        Path("/app/data/processed/summary.txt"),
    ]
    for sp in search_paths:
        if sp.exists():
            try:
                with open(sp) as f:
                    return f.read().strip()
            except IOError:
                continue
    return None


def compute_top_k(products: List[Dict[str, Any]], k: int = 5, weights: Optional[Dict[str, float]] = None):
    """Compute top-K scoring."""
    weights = weights or {"rating": 0.3, "reviews_count": 0.25, "price_competitiveness": 0.2, "availability": 0.15}
    df = pd.DataFrame(products)
    if df.empty:
        return pd.DataFrame()
    max_price = df['price'].max() or 1
    df['_price_score'] = (1 - (df['price'] / max_price)).clip(0, 1)
    max_rating = df['rating'].max() or 5
    df['_rating_score'] = (df['rating'] / max_rating).clip(0, 1)
    max_reviews = df['reviews_count'].max() or 1
    df['_reviews_score'] = (df['reviews_count'] / max_reviews).clip(0, 1)
    df['_availability_score'] = df['availability'].astype(float)
    df['_score'] = (
        weights.get("rating", 0) * df['_rating_score'] +
        weights.get("reviews_count", 0) * df['_reviews_score'] +
        weights.get("price_competitiveness", 0) * df['_price_score'] +
        weights.get("availability", 0) * df['_availability_score']
    )
    df = df.sort_values('_score', ascending=False).reset_index(drop=True)
    return df.head(k)


def render_header():
    st.title("📊 Smart eCommerce Intelligence Dashboard")
    st.markdown("""
    Analyse et sélection de produits e-commerce avec IA. Données scrapées depuis WooCommerce,
    stockées dans PostgreSQL, analysées via Kubeflow Pipelines, et enrichies par LLM (DeepSeek/Groq).
    """)


def render_kpis(df_all, df_top):
    st.subheader("Indicateurs Clés")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total produits", len(df_all))
    col2.metric("Top-K affichés", len(df_top))
    col3.metric("Prix moyen", f"{df_all['price'].mean():.0f} $")
    col4.metric("Note moyenne", f"{df_all['rating'].mean():.2f} ⭐")


def render_filters(df):
    st.sidebar.header("Filtres")
    categories = ["Tous"] + sorted(df['category'].dropna().unique().tolist())
    selected_cat = st.sidebar.selectbox("Catégorie", categories)
    k = st.sidebar.slider("Nombre de Top-K", 1, min(20, len(df)), 10)
    price_range = st.sidebar.slider("Prix (USD)", 0, int(df['price'].max()), (0, int(df['price'].max())))
    return selected_cat, k, price_range


def render_llm_summary(summary_text):
    if summary_text:
        st.subheader("🤖 Résumé LLM (DeepSeek)")
        with st.container():
            st.markdown(f"> {summary_text}")
    else:
        st.info("Aucun résumé LLM disponible. Exécutez le pipeline Kubeflow pour en générer un.")


def render_top_k_table(df_top):
    st.subheader("Top-K Produits")
    show_cols = ["name", "category", "price", "rating", "reviews_count", "availability", "_score"]
    available = [c for c in show_cols if c in df_top.columns]
    display = df_top[available].copy()
    display = display.rename(columns={
        "name": "Produit", "category": "Catégorie", "price": "Prix (USD)",
        "rating": "Note", "reviews_count": "Avis", "availability": "Dispo", "_score": "Score"
    })
    st.dataframe(display, use_container_width=True)


def render_charts(df_all, df_top, selected_cat):
    st.subheader("Visualisations")
    tab1, tab2, tab3 = st.tabs(["Distribution Prix/Note", "Catégories", "Clusters (KMeans)"])

    with tab1:
        fig = px.scatter(df_all, x='price', y='rating', color='category',
                         size='reviews_count', hover_name='name',
                         title="Prix vs. Note (taille = nombre d'avis)")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        cat_counts = df_all['category'].value_counts().reset_index()
        cat_counts.columns = ['category', 'count']
        fig2 = px.pie(cat_counts, values='count', names='category', title="Répartition des catégories")
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        X = df_all[['price', 'rating', 'reviews_count']].values
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)
        n_clusters = min(4, len(df_all))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df_all['_cluster'] = kmeans.fit_predict(Xs)
        fig3 = px.scatter(df_all, x='price', y='rating', color='_cluster',
                          hover_name='name', title=f"Clusters KMeans (K={n_clusters})")
        st.plotly_chart(fig3, use_container_width=True)


def render_mcp_section():
    st.subheader("📡 MCP Server (Model Context Protocol)")
    st.markdown("""
    Le serveur MCP expose des outils pour que les LLMs interagissent avec le système.
    Endpoints : `/tools/scrape_shopify`, `/tools/scrape_woocommerce`, `/tools/analyze_top_k`, `/tools/generate_summary`
    """)


def main():
    render_header()

    # Charger les données (PostgreSQL d'abord)
    products, source = load_products()
    df_all = pd.DataFrame(products)

    # Charger le résumé LLM
    summary = load_summary()
    render_llm_summary(summary)

    # Filtres
    selected_cat, k, price_range = render_filters(df_all)
    mask = (df_all['price'] >= price_range[0]) & (df_all['price'] <= price_range[1])
    if selected_cat != "Tous":
        mask &= (df_all['category'] == selected_cat)
    df_filtered = df_all[mask].copy()

    # Top-K
    df_top = compute_top_k(df_filtered.to_dict('records'), k=k)

    # KPIs
    render_kpis(df_all, df_top)

    # Top-K table
    if not df_top.empty:
        render_top_k_table(df_top)
    else:
        st.warning("Aucun produit ne correspond aux filtres sélectionnés.")

    # Charts
    render_charts(df_filtered, df_top, selected_cat)

    # MCP info
    render_mcp_section()

    # Footer avec source
    st.caption(f"Smart eCommerce Intelligence — {len(products)} produits · Source : {source}")


if __name__ == "__main__":
    main()

run_dashboard = main