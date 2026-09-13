"""
Phase 5 — deterministic TF-IDF + cosine similarity engine for real MPLADS
records. No embeddings, no external models/APIs, no randomness.

Method/version identifier for this batch: "tfidf_cosine_v1"
(documented here and in phase5_computation_config.json — NOT stored per-row,
since the existing WorkSimilarity table has no method/version column and
Phase 5 is explicitly not supposed to redesign the schema for this).
"""
import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

METHOD_VERSION = "tfidf_cosine_v1"

TFIDF_CONFIG = {
    "lowercase": True,
    "stop_words": "english",
    "ngram_range": (1, 2),
    "min_df": 2,
    "max_features": 20000,
    "sublinear_tf": True,
}

# Metadata bonus weights — small and additive on top of text similarity (0-1 scale).
# Capped combined so text similarity always remains the dominant signal.
CATEGORY_BONUS = 0.05
STATE_BONUS = 0.03
HOUSE_BONUS = 0.02
AMOUNT_BONUS_MAX = 0.05
MAX_TOTAL_BONUS = CATEGORY_BONUS + STATE_BONUS + HOUSE_BONUS + AMOUNT_BONUS_MAX  # 0.15

_WHITESPACE_RE = re.compile(r"\s+")
NO_DESCRIPTION_PLACEHOLDER = "No description available in source data."


def normalize_text(text):
    if not text:
        return ""
    text = str(text).strip()
    if text == NO_DESCRIPTION_PLACEHOLDER:
        # This is a structural placeholder we inserted in Phase 2, not real content —
        # including it verbatim would create false similarity between every work that
        # happens to lack a source description.
        return ""
    text = text.lower()
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def build_document(record):
    """Combine name + description + category + state into one text field.
    Deliberately excludes IDs, MP names, dates, and financial values, which
    would create misleading textual similarity."""
    parts = [
        normalize_text(record.get("name")),
        normalize_text(record.get("description")),
        normalize_text(record.get("category")),
        normalize_text(record.get("state")),
    ]
    doc = " ".join(p for p in parts if p)
    return doc


def fit_tfidf(documents):
    vectorizer = TfidfVectorizer(**TFIDF_CONFIG)
    X = vectorizer.fit_transform(documents)
    return vectorizer, X


def compute_top_n_neighbors(X, n=5):
    """Sparse, exact nearest-neighbor cosine search — never materializes a
    dense n x n matrix. Returns (indices, similarities), each shape (n_rows, n),
    excluding self-matches."""
    n_neighbors = n + 1  # +1 to account for self-match, dropped below
    model = NearestNeighbors(metric="cosine", algorithm="brute", n_jobs=1)
    model.fit(X)
    distances, indices = model.kneighbors(X, n_neighbors=n_neighbors)
    similarities = 1.0 - distances  # cosine similarity = 1 - cosine distance

    out_indices = np.zeros((X.shape[0], n), dtype=indices.dtype)
    out_similarities = np.zeros((X.shape[0], n), dtype=float)
    for row in range(X.shape[0]):
        row_idx = indices[row]
        row_sim = similarities[row]
        mask = row_idx != row  # drop self-match wherever it lands
        filtered_idx = row_idx[mask][:n]
        filtered_sim = row_sim[mask][:n]
        k = len(filtered_idx)
        out_indices[row, :k] = filtered_idx
        out_similarities[row, :k] = filtered_sim
        if k < n:
            out_indices[row, k:] = -1  # sentinel: fewer than n valid neighbors
            out_similarities[row, k:] = 0.0
    return out_indices, out_similarities


def amount_proximity_bonus(amount_a, amount_b):
    """0..AMOUNT_BONUS_MAX, higher when two amounts (in lakhs) are close in
    relative terms. Returns 0.0 (no bonus, NOT invented similarity) if either
    is missing."""
    if amount_a is None or amount_b is None:
        return 0.0
    if amount_a <= 0 and amount_b <= 0:
        return AMOUNT_BONUS_MAX
    max_amt = max(amount_a, amount_b, 1e-9)
    diff = abs(amount_a - amount_b)
    closeness = max(0.0, 1.0 - diff / max_amt)
    return AMOUNT_BONUS_MAX * closeness


def compute_metadata_bonus(record_a, record_b):
    bonus = 0.0
    if record_a.get("category") and record_a.get("category") == record_b.get("category"):
        bonus += CATEGORY_BONUS
    if record_a.get("state") and record_a.get("state") == record_b.get("state"):
        bonus += STATE_BONUS
    if record_a.get("house") and record_a.get("house") == record_b.get("house"):
        bonus += HOUSE_BONUS
    bonus += amount_proximity_bonus(record_a.get("recommended_amount"), record_b.get("recommended_amount"))
    return bonus


def final_similarity(text_similarity, bonus):
    return min(1.0, float(text_similarity) + float(bonus))
