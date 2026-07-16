"""Core Tags layer — tag normalization, storage, and recommendations.

Public API:
    normalizer:
        TagNormalizer  — Unicode NFC + whitespace + lowercase + alias resolution
        normalize()    — Convenience single-tag normalizer

    cooccurrence:
        CooccurrenceEngine  — Jaccard-based tag co-occurrence recommender
        TagCooccurrence     — Result dataclass (tag_id, tag_name, score)
"""
