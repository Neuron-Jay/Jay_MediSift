"""Save selected citation records into MediSift's existing single-paper library."""

from pathlib import Path

from .models import Article

LIBRARY_DIR = Path("text_file_repository")


def download_article(article: Article) -> Path:
    """Save a .txt citation record directly readable by deep_agent."""
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    record_path = LIBRARY_DIR / f"pubmed_{article.pmid}.txt"
    metadata = [
        f"Title: {article.title}",
        f"Authors: {', '.join(article.authors)}",
        f"Journal: {article.journal}",
        f"Publication date: {article.publication_date}",
        f"Publication types: {', '.join(article.publication_types)}",
        f"MeSH terms: {', '.join(article.mesh_terms)}",
        f"DOI: {article.doi}",
        f"PMID: {article.pmid}",
        f"PubMed: {article.pubmed_url}",
        f"PMC: https://pmc.ncbi.nlm.nih.gov/articles/{article.pmc_id}/" if article.pmc_id else "PMC: Not available",
        "",
        "Abstract:",
        article.abstract or "No abstract is available in PubMed.",
    ]
    record_path.write_text("\n".join(metadata), encoding="utf-8")
    return record_path
