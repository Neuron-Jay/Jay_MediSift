"""Batch LLM relevance ranking for normalized PubMed records."""

from .llm import rank_batch
from .models import Article, RankedArticle, SearchRequest

LABELS = {"Highly relevant", "Relevant", "Possibly relevant", "Low relevance"}
ORDER = {"Highly relevant": 0, "Relevant": 1, "Possibly relevant": 2, "Low relevance": 3}


def rank_articles(request: SearchRequest, articles: list[Article], limit: int = 50) -> list[RankedArticle]:
    candidates = articles[:limit]
    summary = request.original_text
    result_by_pmid: dict[str, RankedArticle] = {
        article.pmid: RankedArticle(article=article) for article in candidates
    }
    # Small batches keep the prompt bounded and allow a failed batch to degrade gracefully.
    for start in range(0, len(candidates), 10):
        batch = candidates[start:start + 10]
        payload = [{
            "pmid": article.pmid,
            "title": article.title,
            "abstract": article.abstract[:3500],
            "publication_types": article.publication_types,
            "mesh_terms": article.mesh_terms[:30],
        } for article in batch]
        try:
            rankings = rank_batch(summary, payload)
        except Exception:
            continue
        for item in rankings:
            if not isinstance(item, dict):
                continue
            ranked = result_by_pmid.get(str(item.get("pmid", "")))
            if ranked is None:
                continue
            label = item.get("relevance")
            if label in LABELS:
                ranked.relevance = label
            reason = item.get("reason")
            if isinstance(reason, str) and reason.strip():
                ranked.reason = reason.strip()[:400]
    return sorted(result_by_pmid.values(), key=lambda item: ORDER[item.relevance])
