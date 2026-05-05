import logging
from typing import Any, Dict, List, Optional

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import core modules gracefully
try:
    from src.__main__ import SmartECommerceIntelligence
    from src.data_analysis.evaluation import evaluate_clustering
    CORE_AVAILABLE = True
except Exception:
    CORE_AVAILABLE = False
    logger.warning("Core modules not available; dashboard will run in demo mode.")


# Page config
st.set_page_config(page_title="Smart eCommerce Intelligence", page_icon="📊", layout="wide")


def load_sample_data():
    """Return a small sample dataset for demo."""
    return [
        {"product_id": "1", "name": "Wireless Earbuds", "category": "Electronics", "price": 59.0, "rating": 4.6, "reviews_count": 1200, "availability": True, "vendor": "TechStore", "quantity": 35},
        {"product_id": "2", "name": "Fitness Tracker", "category": "Sport", "price": 49.0, "rating": 4.2, "reviews_count": 340, "availability": True, "vendor": "FitShop", "quantity": 10},
        {"product_id": "3", "name": "LED Desk Lamp", "category": "Home", "price": 29.0, "rating": 4.8, "reviews_count": 980, "availability": True, "vendor": "BrightHome", "quantity": 80},
        {"product_id": "4", "name": "Bluetooth Speaker", "category": "Electronics", "price": 79.0, "rating": 4.4, "reviews_count": 450, "availability": False, "vendor": "SoundCo", "quantity": 0},
        {"product_id": "5", "name": "Yoga Mat", "category": "Sport", "price": 25.0, "rating": 4.7, "reviews_count": 2100, "availability": True, "vendor": "FitShop", "quantity": 120},
        {"product_id": "6", "name": "Smart Watch", "category": "Electronics", "price": 199.0, "rating": 4.5, "reviews_count": 780, "availability": True, "vendor": "TechStore", "quantity": 15},
        {"product_id": "7", "name": "Coffee Maker", "category": "Home", "price": 89.0, "rating": 4.3, "reviews_count": 560, "availability": True, "vendor": "BrewMaster", "quantity": 22},
        {"product_id": "8", "name": "Running Shoes", "category": "Sport", "price": 110.0, "rating": 4.6, "reviews_count": 1340, "availability": True, "vendor": "RunPro", "quantity": 45},
    ]


def compute_top_k(products: List[Dict[str, Any]], k: int = 5, weights: Optional[Dict[str, float]] = None):
    """Compute top-K scoring."""
    weights = weights or {"rating": 0.3, "reviews_count": 0.25, "price_competitiveness": 0.2, "availability": 0.15}
    df = pd.DataFrame(products)
    if df.empty:
        return pd.DataFrame()
    # Normalize metrics
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
    Analyse et sélection de produits e-commerce avec IA. Scrapez des données, identifiez les meilleurs produits (Top-K),
    et explorez les clusters avec des algorithmes de Machine Learning.
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
    categories = ["Tous"] + sorted(df['category'].unique().tolist())
    selected_cat = st.sidebar.selectbox("Catégorie", categories)
    k = st.sidebar.slider("Nombre de Top-K", 1, min(20, len(df)), 5)
    price_range = st.sidebar.slider("Prix (USD)", 0, int(df['price'].max()), (0, int(df['price'].max())))
    return selected_cat, k, price_range


def render_top_k_table(df_top):
    st.subheader("Top-K Produits")
    show_cols = ["name", "category", "price", "rating", "reviews_count", "availability", "_score"]
    display = df_top[show_cols].copy()
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
        # Simple KMeans on price, rating, reviews
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
    Exemples d'outils disponibles :
    - `scrape_shopify` - Scraper un produit Shopify
    - `scrape_woocommerce` - Scraper un produit WooCommerce
    - `analyze_top_k` - Analyser et retourner les Top-K produits
    - `generate_summary` - Générer un résumé avec LLM
    """)
    st.code("""
    # Exemple d'appel MCP via HTTP
    POST /tools/analyze_top_k
    Headers: { "x-api-key": "votre_cle_api" }
    Body: {
      "products": [ { "name": "...", "price": 10, "rating": 4.5, ... } ],
      "k": 5
    }
    """, language="json")


def main():
    render_header()

    # Load data
    products = load_sample_data()
    df_all = pd.DataFrame(products)

    # Filters
    selected_cat, k, price_range = render_filters(df_all)
    # Apply filters
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

    # Footer
    st.caption("Smart eCommerce Intelligence — Dashboard de démonstration")


if __name__ == "__main__":
    main()

# Expose the main function as run_dashboard for backward compatibility
run_dashboard = main

