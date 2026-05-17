"""
Analyse Concurrentielle LLM
============================
Module d'analyse concurrentielle augmentée par LLM (Groq uniquement).

Fonctionnalités :
1. Comparaison automatique de produits concurrents
2. Génération de rapports de produits émergents
3. Recommandations stratégiques marketing

Utilisation exclusive de Groq (llama-3.3-70b-versatile).
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CompetitiveAnalysis:
    """Analyse concurrentielle des produits eCommerce via LLM (Groq)."""

    def __init__(self, groq_key: str):
        """
        Initialise l'analyseur concurrentiel.
        
        Args:
            groq_key: Clé API Groq (obligatoire)
        """
        if not groq_key:
            raise ValueError("GROQ_API_KEY est requis pour l'analyse concurrentielle")
        from src.llm.wrapper import LLMWrapper
        self.llm = LLMWrapper(groq_key=groq_key)
        self.groq_key = groq_key

    # ============================================================
    # 1. Comparaison automatique de produits concurrents
    # ============================================================

    def compare_products(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare automatiquement les produits concurrents par catégorie
        et génère une analyse détaillée des forces et faiblesses.

        Args:
            products: Liste des produits scrapés (avec nom, prix, note, catégorie, etc.)

        Returns:
            Dict avec analyse concurrentielle structurée
        """
        if not products or len(products) < 2:
            return {
                "status": "insufficient_data",
                "message": "Besoin d'au moins 2 produits pour une analyse concurrentielle",
                "comparisons": [],
                "generated_at": datetime.now().isoformat(),
            }

        # Grouper par catégorie
        from collections import defaultdict
        categories: Dict[str, List[Dict]] = defaultdict(list)
        for p in products:
            cat = p.get("category", "Non classé")
            categories[cat].append(p)

        comparisons = []
        for cat, cat_products in categories.items():
            if len(cat_products) < 2:
                continue

            # Trier par score (rating * reviews) pour identifier les leaders
            sorted_prods = sorted(
                cat_products,
                key=lambda x: (x.get("rating", 0) or 0) * (x.get("reviews_count", 0) or 0),
                reverse=True,
            )

            top_products = sorted_prods[:5]  # Top 5 par catégorie
            comparison = self._generate_category_comparison(cat, top_products)
            comparisons.append(comparison)

        return {
            "status": "completed",
            "total_products_analyzed": len(products),
            "categories_analyzed": len(comparisons),
            "comparisons": comparisons,
            "generated_at": datetime.now().isoformat(),
        }

    def _generate_category_comparison(self, category: str, products: List[Dict]) -> Dict[str, Any]:
        """Generate LLM comparison for products in a category."""
        # Build product data text
        product_lines = []
        for i, p in enumerate(products, 1):
            name = p.get("name", "Unknown")
            price = p.get("price", 0)
            rating = p.get("rating", 0)
            reviews = p.get("reviews_count", 0)
            vendor = p.get("vendor", "Unknown")
            avail = "Oui" if p.get("availability") else "Non"
            product_lines.append(
                f"{i}. {name} | Vendeur: {vendor} | Prix: {price}$ | "
                f"Note: {rating}/5 | Avis: {reviews} | Disponible: {avail}"
            )

        prompt = (
            "Tu es un analyste concurrentiel eCommerce expert. "
            "Analyse ces produits concurrents dans la catégorie suivante.\n\n"
            f"CATÉGORIE : {category}\n\n"
            "PRODUITS :\n"
            + "\n".join(product_lines)
            + "\n\n"
            "Rédige une analyse concurrentielle structurée en français. "
            "Inclus obligatoirement ces sections :\n"
            "1. RAPPORT DE FORCES : Qui domine et pourquoi ? (leader, challenger)\n"
            "2. COMPARAISON PRIX : Qui est le plus cher/moins cher ? Rapport qualité/prix ?\n"
            "3. POSITIONNEMENT : Forces et faiblesses de chaque produit\n"
            "4. RECOMMANDATION : Stratégie recommandée pour se démarquer\n\n"
            "Sois précis, cite les noms des produits et les chiffres. "
            "Format clair avec titres en MAJUSCULES."
        )

        try:
            analysis = self._call_groq(prompt, max_tokens=1500, temperature=0.5)
        except Exception as e:
            logger.error(f"LLM comparison failed for category {category}: {e}")
            analysis = f"Analyse indisponible pour {category}: {e}"

        return {
            "category": category,
            "products_compared": len(products),
            "product_names": [p.get("name", "Unknown") for p in products],
            "price_range": {
                "min": round(min(p.get("price", 0) for p in products), 2),
                "max": round(max(p.get("price", 0) for p in products), 2),
                "avg": round(sum(p.get("price", 0) for p in products) / len(products), 2),
            },
            "avg_rating": round(sum(p.get("rating", 0) or 0 for p in products) / len(products), 2),
            "analysis_text": analysis,
        }

    # ============================================================
    # 2. Génération de rapports de produits émergents
    # ============================================================

    def generate_emerging_report(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Génère un rapport des produits émergents (top tendances de la semaine).

        Analyse croisée :
        - Produits avec forte hausse d'avis récents
        - Nouveaux produits détectés
        - Produits avec baisse de prix agressive
        - Produits avec amélioration de note

        Args:
            products: Liste des produits scrapés

        Returns:
            Rapport structuré des produits émergents
        """
        if not products:
            return {
                "status": "insufficient_data",
                "message": "Aucun produit à analyser",
                "emerging_products": [],
                "generated_at": datetime.now().isoformat(),
            }

        # Scoring d'émergence basé sur les données disponibles
        scored = []
        for p in products:
            rating = p.get("rating", 0) or 0
            reviews = p.get("reviews_count", 0) or 0
            price = p.get("price", 0) or 0
            avail = 1 if p.get("availability") else 0

            # Score d'émergence composite
            # Un produit émergent a : bonne note + beaucoup d'avis récents + prix attractif
            emergence_score = (
                (rating / 5.0) * 0.35  # Note (max 35%)
                + min(reviews / 500, 1.0) * 0.35  # Avis (max 35%)
                + (1.0 - min(price / 200, 1.0)) * 0.20  # Prix attractif (max 20%)
                + avail * 0.10  # Disponibilité (max 10%)
            )

            scored.append({
                **p,
                "_emergence_score": round(emergence_score, 4),
            })

        # Trier par score d'émergence
        scored.sort(key=lambda x: x["_emergence_score"], reverse=True)
        top_emerging = scored[:10]  # Top 10 émergents

        # Générer le rapport LLM
        report = self._generate_emerging_report_text(top_emerging, products)

        return {
            "status": "completed",
            "total_products_analyzed": len(products),
            "top_emerging_count": len(top_emerging),
            "emerging_products": [
                {
                    "rank": i + 1,
                    "name": p.get("name", "Unknown"),
                    "category": p.get("category", ""),
                    "price": p.get("price", 0),
                    "rating": p.get("rating", 0),
                    "reviews_count": p.get("reviews_count", 0),
                    "emergence_score": p["_emergence_score"],
                }
                for i, p in enumerate(top_emerging)
            ],
            "report_text": report,
            "generated_at": datetime.now().isoformat(),
        }

    def _generate_emerging_report_text(self, top_emerging: List[Dict], all_products: List[Dict]) -> str:
        """Generate LLM report text for emerging products."""
        if not top_emerging:
            return "Aucun produit émergent détecté."

        product_lines = []
        for i, p in enumerate(top_emerging[:7], 1):
            name = p.get("name", "Unknown")
            cat = p.get("category", "?")
            price = p.get("price", 0)
            rating = p.get("rating", 0)
            reviews = p.get("reviews_count", 0)
            score = p.get("_emergence_score", 0)
            product_lines.append(
                f"{i}. {name} | Cat: {cat} | Prix: {price}$ | "
                f"Note: {rating}/5 | {reviews} avis | Score: {score:.3f}"
            )

        prompt = (
            "Tu es un analyste de tendances eCommerce. "
            "Génère un RAPPORT HEBDOMADAIRE DES PRODUITS ÉMERGENTS en français.\n\n"
            f"Produits analysés au total : {len(all_products)}\n\n"
            "TOP 7 PRODUITS ÉMERGIENTS DÉTECTÉS :\n"
            + "\n".join(product_lines)
            + "\n\n"
            "Structure obligatoire du rapport :\n"
            "📈 TOP PRODUITS QUI MONTENT : Décris chaque produit et pourquoi il est émergent\n"
            "📊 TENDANCES PAR CATÉGORIE : Quelles catégories sont en croissance ?\n"
            "💡 OPPORTUNITÉS : Quels produits/segments ont le plus de potentiel ?\n"
            "⚠️ SIGNAL FAIBLE : Détecte les tendances naissantes\n\n"
            "Sois précis et actionnable. Utilise des émojis pour structurer."
        )

        try:
            return self._call_groq(prompt, max_tokens=2000, temperature=0.6)
        except Exception as e:
            logger.error(f"Emerging report generation failed: {e}")
            return f"Rapport indisponible: {e}"

    # ============================================================
    # 3. Recommandations stratégiques marketing
    # ============================================================

    def generate_strategic_recommendations(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Génère des recommandations stratégiques marketing basées sur l'analyse
        complète des données produits.

        Analyse :
        - Prix : segments sous-évalués ou sur-évalués
        - Stock : ruptures et opportunités
        - Catégories : niches et segments porteurs
        - Concurrents : positions de force et faiblesses

        Args:
            products: Liste des produits scrapés

        Returns:
            Recommandations stratégiques structurées
        """
        if not products:
            return {
                "status": "insufficient_data",
                "message": "Aucun produit à analyser",
                "recommendations": [],
                "generated_at": datetime.now().isoformat(),
            }

        # Analyses de base
        from collections import defaultdict
        categories: Dict[str, List[float]] = defaultdict(list)
        total_stock_low = 0
        total_products = len(products)
        categories_avail: Dict[str, int] = defaultdict(int)

        for p in products:
            cat = p.get("category", "Non classé")
            price = p.get("price", 0) or 0
            categories[cat].append(price)
            if not p.get("availability", True):
                categories_avail[cat] += 1

        # Identifier les segments sous-évalués (prix bas vs note haute)
        segments_data = []
        for cat, prices in categories.items():
            avg_price = sum(prices) / len(prices)
            category_products = [p for p in products if p.get("category") == cat]
            avg_rating = sum(p.get("rating", 0) or 0 for p in category_products) / len(category_products)
            out_of_stock = sum(1 for p in category_products if not p.get("availability", True))
            segments_data.append({
                "category": cat,
                "product_count": len(category_products),
                "avg_price": round(avg_price, 2),
                "avg_rating": round(avg_rating, 2),
                "out_of_stock": out_of_stock,
                "value_score": round(avg_rating / (avg_price / 10 + 1), 4),  # Higher = better value
            })

        segments_data.sort(key=lambda x: x["value_score"], reverse=True)

        # Générer les recommandations LLM
        recommendations_text = self._generate_recommendations_text(products, segments_data)

        return {
            "status": "completed",
            "total_products_analyzed": total_products,
            "segments_analyzed": len(segments_data),
            "segments": segments_data[:8],  # Top 8 segments
            "recommendations_text": recommendations_text,
            "generated_at": datetime.now().isoformat(),
        }

    def _generate_recommendations_text(self, products: List[Dict], segments: List[Dict]) -> str:
        """Generate LLM strategic recommendations."""
        segment_lines = []
        for s in segments[:6]:
            segment_lines.append(
                f"- {s['category']}: {s['product_count']} produits, "
                f"prix moyen {s['avg_price']}$, note {s['avg_rating']}/5, "
                f"{s['out_of_stock']} ruptures"
            )

        # Stats globales
        prices = [p.get("price", 0) or 0 for p in products]
        ratings = [p.get("rating", 0) or 0 for p in products]
        avg_price = sum(prices) / len(prices) if prices else 0
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        max_price = max(prices) if prices else 0
        min_price = min(prices) if prices else 0

        prompt = (
            "Tu es un consultant en stratégie marketing eCommerce de haut niveau. "
            "Analyse ces données et génère des RECOMMANDATIONS STRATÉGIQUES en français.\n\n"
            "CONTEXTE GLOBAL :\n"
            f"- Produits analysés : {len(products)}\n"
            f"- Prix moyen : {avg_price:.0f}$\n"
            f"- Note moyenne : {avg_rating:.2f}/5\n"
            f"- Fourchette de prix : {min_price:.0f}$ - {max_price:.0f}$\n\n"
            "SEGMENTS ANALYSÉS :\n"
            + "\n".join(segment_lines)
            + "\n\n"
            "Structure obligatoire du rapport :\n"
            "🎯 RECOMMANDATIONS PRIX : Quels segments sont sous-évalués ? Sur-évalués ?\n"
            "📦 GESTION STOCK : Quels produits risquent des ruptures ?\n"
            "🚀 OPPORTUNITÉS MARCHÉ : Quelles niches attaquer ?\n"
            "⚔️ POSITIONNEMENT CONCURRENTIEL : Comment se différencier ?\n"
            "📋 PLAN D'ACTION : Top 3 actions concrètes avec priorités\n\n"
            "Sois très concret, donne des chiffres et des actions précises."
        )

        try:
            return self._call_groq(prompt, max_tokens=2500, temperature=0.5)
        except Exception as e:
            logger.error(f"Strategic recommendations failed: {e}")
            return f"Recommandations indisponibles: {e}"

    # ============================================================
    # Appel Groq centralisé
    # ============================================================

    def _call_groq(self, prompt: str, max_tokens: int = 1500, temperature: float = 0.5) -> str:
        """Centralized Groq-only call."""
        import httpx

        # Modèle performant pour l'analyse
        model = "llama-3.3-70b-versatile"

        try:
            resp = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Groq competitive analysis error: {e}")
            raise

    # ============================================================
    # Analyse complète (les 3 en un)
    # ============================================================

    def run_full_analysis(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Exécute les 3 analyses concurrentielles d'un coup.

        Args:
            products: Liste des produits scrapés

        Returns:
            Rapport complet avec les 3 analyses
        """
        logger.info(f"Starting full competitive analysis on {len(products)} products")

        comparison = self.compare_products(products)
        emerging = self.generate_emerging_report(products)
        recommendations = self.generate_strategic_recommendations(products)

        result = {
            "status": "completed",
            "total_products": len(products),
            "generated_at": datetime.now().isoformat(),
            "competitive_comparison": comparison,
            "emerging_report": emerging,
            "strategic_recommendations": recommendations,
        }

        logger.info("Full competitive analysis completed")
        return result


# ============================================================
# Fonction utilitaire pour le Dashboard
# ============================================================

def generate_competitive_insights(products: List[Dict[str, Any]], groq_key: str) -> Dict[str, Any]:
    """Point d'entrée simple pour le dashboard."""
    if not products:
        return {
            "status": "no_data",
            "message": "Aucun produit à analyser",
            "generated_at": datetime.now().isoformat(),
        }
    if not groq_key:
        return {
            "status": "no_groq_key",
            "message": "GROQ_API_KEY non configurée",
            "generated_at": datetime.now().isoformat(),
        }

    try:
        analyzer = CompetitiveAnalysis(groq_key=groq_key)
        return analyzer.run_full_analysis(products)
    except Exception as e:
        logger.error(f"Competitive analysis failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "generated_at": datetime.now().isoformat(),
        }


__all__ = [
    "CompetitiveAnalysis",
    "generate_competitive_insights",
]