"""Deterministic conversion from SearchRequest to PubMed syntax."""

from .models import SearchRequest


def _phrase(value: str) -> str:
    # PubMed terms are quoted; escape embedded quotes rather than allowing syntax injection.
    return '"' + value.replace('"', "") + '"'


def _term_group(terms: list[str], field: str = "Title/Abstract") -> str:
    parts = []
    for term in terms:
        clean = term.strip()
        if clean:
            parts.append(f"{_phrase(clean)}[{field}]")
    return "(" + " OR ".join(parts) + ")" if parts else ""


def build_pubmed_query(request: SearchRequest) -> str:
    clauses: list[str] = []
    for concept in request.concepts:
        terms = _term_group(concept.get("terms", []))
        mesh = _term_group(concept.get("mesh_terms", []), "Mesh")
        if terms and mesh:
            clauses.append(f"({terms} OR {mesh})")
        elif terms or mesh:
            clauses.append(terms or mesh)

    if request.study_types:
        clauses.append(_term_group(request.study_types))
    if request.publication_types:
        clauses.append(_term_group(request.publication_types, "Publication Type"))
    if request.species:
        species_mesh = "Animals" if request.species == "animals" else "Humans"
        clauses.append(f'"{species_mesh}"[Mesh]')
    if request.require_abstract:
        clauses.append('hasabstract')
    if request.date_from or request.date_to:
        start = request.date_from or "1800/01/01"
        end = request.date_to or "3000/12/31"
        clauses.append(f'("{start}"[Date - Publication] : "{end}"[Date - Publication])')
    query = " AND ".join(clauses) if clauses else "all[sb]"
    if request.exclude_publication_types:
        excluded = _term_group(request.exclude_publication_types, "Publication Type")
        query = f"({query}) NOT {excluded}"
    return query
