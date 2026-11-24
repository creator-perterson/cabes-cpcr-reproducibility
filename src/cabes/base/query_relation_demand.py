"""CABES-v0.1.2 query-relation decomposition public API."""
from .query_constraint_parser import decompose_query

def extract_query_relation_demand(question_id: str, question: str, evidence: list[dict], lexicon=None) -> dict:
    return decompose_query(question_id, question, evidence)


