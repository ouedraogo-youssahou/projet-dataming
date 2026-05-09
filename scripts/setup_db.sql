-- ============================================
-- Smart eCommerce Intelligence - Schéma PostgreSQL
-- ============================================

-- Table des produits scrapés
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(255) UNIQUE,
    name TEXT,
    description TEXT,
    category VARCHAR(255),
    price REAL DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'USD',
    availability BOOLEAN DEFAULT TRUE,
    quantity INT,
    rating REAL DEFAULT 0,
    reviews_count INT DEFAULT 0,
    images TEXT[],
    tags TEXT[],
    vendor VARCHAR(255),
    source VARCHAR(50) DEFAULT 'woocommerce',
    scraped_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Table des résultats ML (clustering, classification)
CREATE TABLE IF NOT EXISTS ml_results (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(255),
    model_type VARCHAR(50),      -- 'kmeans', 'dbscan', 'random_forest', 'xgboost', 'top_k'
    metrics JSONB,               -- silhouette, accuracy, noise, etc.
    results JSONB,               -- clusters, top_k products, feature importance
    n_products INT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table des résumés LLM
CREATE TABLE IF NOT EXISTS summaries (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(255),
    pipeline_name VARCHAR(255),
    summary_text TEXT,
    n_products INT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table des runs de pipeline
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(255) UNIQUE,
    pipeline_name VARCHAR(255),
    status VARCHAR(50),
    n_products_scraped INT DEFAULT 0,
    n_features INT DEFAULT 0,
    models_trained INT DEFAULT 0,
    top_k_count INT DEFAULT 0,
    summary_length INT DEFAULT 0,
    started_at TIMESTAMP DEFAULT NOW(),
    finished_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index pour les recherches fréquentes
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_rating ON products(rating);
CREATE INDEX IF NOT EXISTS idx_ml_results_run ON ml_results(run_id);
CREATE INDEX IF NOT EXISTS idx_ml_results_model ON ml_results(model_type);
CREATE INDEX IF NOT EXISTS idx_summaries_run ON summaries(run_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_run ON pipeline_runs(run_id);

-- Vue pour le Top-K (basée sur un scoring pondéré)
CREATE OR REPLACE VIEW top_k_products AS
SELECT 
    id,
    product_id,
    name,
    category,
    price,
    rating,
    reviews_count,
    availability,
    -- Score pondéré (mêmes poids que dans le code)
    (0.3 * COALESCE(rating / NULLIF((SELECT MAX(rating) FROM products), 0), 0) +
     0.25 * COALESCE(reviews_count::float / NULLIF((SELECT MAX(reviews_count) FROM products)::float, 0), 0) +
     0.2 * COALESCE(1 - (price / NULLIF((SELECT MAX(price) FROM products), 0)), 0) +
     0.15 * CASE WHEN availability THEN 1 ELSE 0 END) AS score
FROM products
ORDER BY score DESC;

-- Fonction pour mettre à jour le timestamp updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger pour mettre à jour updated_at automatiquement
DROP TRIGGER IF EXISTS trg_products_updated ON products;
CREATE TRIGGER trg_products_updated
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Insertion des 74 produits depuis products.json
-- (sera fait par le script Python)