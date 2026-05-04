import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

logger = logging.getLogger(__name__)


class AssociationEngine:
    """Association rule mining for product basket analysis."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def find_rules(
        self,
        transactions: List[List[str]],
        min_support: float = 0.05,
        min_confidence: float = 0.5,
        min_lift: float = 1.0,
        max_len: int = 5,
    ) -> Dict[str, Any]:
        """
        Find association rules from transaction lists.
        transactions: list of lists, e.g. [['milk','bread'], ['beer','diapers']]
        """
        # Convert to one-hot DataFrame
        all_items = sorted(set(item for t in transactions for item in t))
        if not all_items:
            return {"rules": [], "summary": {}}

        df = pd.DataFrame(0, index=range(len(transactions)), columns=all_items)
        for i, tx in enumerate(transactions):
            for item in tx:
                if item in df.columns:
                    df.at[i, item] = 1

        # Apriori
        try:
            frequent_itemsets = apriori(df, min_support=min_support, use_colnames=True, max_len=max_len)
            if len(frequent_itemsets) == 0:
                return {"rules": [], "summary": {"frequent_itemsets": 0}}

            rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence)
            if len(rules) == 0:
                return {"rules": [], "summary": {"frequent_itemsets": len(frequent_itemsets)}}

            # Filter by lift
            rules = rules[rules['lift'] >= min_lift].copy()
            rules = rules.sort_values('lift', ascending=False)

            # Format rules
            rule_list = []
            for _, row in rules.iterrows():
                antecedents = list(row['antecedents'])
                consequents = list(row['consequents'])
                rule_list.append({
                    "antecedents": antecedents,
                    "consequents": consequents,
                    "support": float(row['support']),
                    "confidence": float(row['confidence']),
                    "lift": float(row['lift']),
                    "leverage": float(row.get('leverage', 0)),
                    "conviction": float(row.get('conviction', 0)),
                })

            return {
                "rules": rule_list,
                "summary": {
                    "frequent_itemsets": len(frequent_itemsets),
                    "total_rules": len(rule_list),
                    "min_support": min_support,
                    "min_confidence": min_confidence,
                    "min_lift": min_lift,
                },
            }
        except Exception as e:
            logger.error(f"Association rule mining error: {e}")
            return {"rules": [], "summary": {"error": str(e)}}

    def encode_transactions_from_products(
        self,
        products: List[Dict[str, Any]],
        category_field: str = "category",
        top_n_categories: Optional[int] = None,
    ) -> tuple:
        """
        Create synthetic transactions from product categories.
        Returns (transactions list, mapping info).
        """
        # Group products by some heuristic (e.g., by vendor or by proximity in list)
        # Simple: use sliding windows of 3 products as 'baskets'
        categories = []
        for p in products:
            cat = p.get(category_field) or "uncategorized"
            categories.append(cat)

        # Create transactions from sliding windows
        window = 3
        transactions = []
        for i in range(0, len(categories) - window + 1, window):
            tx = categories[i:i + window]
            transactions.append(tx)

        # If not enough, just use all as one transaction
        if not transactions and categories:
            transactions.append(categories)

        return transactions, {"method": "sliding_window_3", "n_products": len(products)}
