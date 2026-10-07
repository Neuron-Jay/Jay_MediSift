"""Typed data models shared by the PubMed workflow."""

from dataclasses import dataclass, field


@dataclass
class SearchRequest:
    original_text: str
    # Each concept is a synonym group; groups are ANDed, synonyms are ORed.
    concepts: list[dict[str, list[str]]] = field(default_factory=list)
    study_types: list[str] = field(default_factory=list)
    publication_types: list[str] = field(default_factory=list)
    exclude_publication_types: list[str] = field(default_factory=list)
    date_from: str | None = None
    date_to: str | None = None
    species: str | None = None  # "animals", "humans", or None
    require_abstract: bool = True

    @classmethod
    def from_dict(cls, data: dict, original_text: str) -> "SearchRequest":
        def strings(key: str) -> list[str]:
            value = data.get(key, [])
            if isinstance(value, str):
                value = [value]
            if not isinstance(value, list):
                return []
            return [str(item).strip() for item in value if str(item).strip()]

        species = data.get("species")
        if species not in ("animals", "humans"):
            species = None
        raw_concepts = data.get("concepts", [])
        concepts: list[dict[str, list[str]]] = []
        if isinstance(raw_concepts, list):
            for item in raw_concepts:
                if isinstance(item, dict):
                    terms = item.get("terms", [])
                    mesh = item.get("mesh_terms", [])
                    if isinstance(terms, str):
                        terms = [terms]
                    if isinstance(mesh, str):
                        mesh = [mesh]
                    concepts.append({
                        "terms": [str(x).strip() for x in terms if str(x).strip()] if isinstance(terms, list) else [],
                        "mesh_terms": [str(x).strip() for x in mesh if str(x).strip()] if isinstance(mesh, list) else [],
                    })
                elif str(item).strip():
                    concepts.append({"terms": [str(item).strip()], "mesh_terms": []})
        return cls(
            original_text=original_text,
            concepts=concepts,
            study_types=strings("study_types"),
            publication_types=strings("publication_types"),
            exclude_publication_types=strings("exclude_publication_types"),
            date_from=_normalize_date(data.get("date_from")),
            date_to=_normalize_date(data.get("date_to")),
            species=species,
            require_abstract=bool(data.get("require_abstract", True)),
        )


def _normalize_date(value: object) -> str | None:
    if value is None or str(value).strip().lower() in {"", "none", "null"}:
        return None
    text = str(value).strip()
    if len(text) == 4 and text.isdigit():
        return f"{text}/01/01"
    if len(text) == 7 and text[4] == "-":
        return f"{text[:4]}/{text[5:7]}/01"
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return text.replace("-", "/")
    return None


@dataclass
class Article:
    pmid: str
    title: str
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    journal: str = ""
    publication_date: str = ""
    publication_types: list[str] = field(default_factory=list)
    mesh_terms: list[str] = field(default_factory=list)
    doi: str = ""
    pmc_id: str = ""

    @property
    def pubmed_url(self) -> str:
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"


@dataclass
class RankedArticle:
    article: Article
    relevance: str = "Possibly relevant"
    reason: str = "AI 排序未能提供判断；请查看原文摘要。"
