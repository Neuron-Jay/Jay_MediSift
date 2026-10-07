"""NCBI E-utilities client and PubMed XML normalization."""

import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date

from dotenv import load_dotenv

from .models import Article, SearchRequest
from .query_builder import build_pubmed_query

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
USER_AGENT = "Jay_MediSift/1.0 (PubMed literature search)"


def _request(endpoint: str, params: dict) -> bytes:
    load_dotenv()
    params = {k: v for k, v in params.items() if v is not None}
    params.setdefault("tool", "Jay_MediSift")
    email = os.getenv("NCBI_EMAIL")
    if email:
        params.setdefault("email", email)
    api_key = os.getenv("NCBI_API_KEY")
    if api_key:
        params.setdefault("api_key", api_key)
    url = BASE_URL + endpoint + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def _text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def _article_date(article: ET.Element) -> str:
    candidates = [
        article.find(".//PubDate"),
        article.find(".//ArticleDate"),
    ]
    for node in candidates:
        if node is None:
            continue
        year = _text(node.find("Year")) or _text(node.find("MedlineDate"))[:4]
        month = _text(node.find("Month")) or "01"
        day = _text(node.find("Day")) or "01"
        months = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06", "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"}
        month = months.get(month[:3], month)
        if year[:4].isdigit():
            try:
                return date(int(year[:4]), int(month), int(day)).isoformat()
            except ValueError:
                return year[:4]
    return ""


def parse_articles(xml_bytes: bytes) -> list[Article]:
    root = ET.fromstring(xml_bytes)
    articles: list[Article] = []
    for node in root.findall(".//PubmedArticle"):
        medline = node.find(".//MedlineCitation")
        article_node = node.find(".//MedlineCitation/Article")
        if medline is None or article_node is None:
            continue
        pmid = _text(medline.find("PMID"))
        title = _text(article_node.find("ArticleTitle"))
        abstracts = [_text(part) for part in article_node.findall(".//Abstract/AbstractText")]
        authors = []
        for author in article_node.findall(".//AuthorList/Author"):
            name = " ".join(filter(None, [_text(author.find("ForeName")), _text(author.find("LastName"))]))
            if not name:
                name = _text(author.find("CollectiveName"))
            if name:
                authors.append(name)
        pub_types = [_text(x) for x in article_node.findall(".//PublicationTypeList/PublicationType") if _text(x)]
        mesh = [_text(x.find("DescriptorName")) for x in medline.findall(".//MeshHeading") if _text(x.find("DescriptorName"))]
        doi = pmc = ""
        for identifier in node.findall(".//PubmedData/ArticleIdList/ArticleId"):
            kind = identifier.attrib.get("IdType", "")
            if kind == "doi":
                doi = _text(identifier)
            elif kind == "pmc":
                pmc = _text(identifier)
        journal_node = article_node.find("Journal")
        articles.append(Article(
            pmid=pmid,
            title=title,
            abstract="\n".join(abstracts),
            authors=authors,
            journal=_text(journal_node.find("Title")) if journal_node is not None else "",
            publication_date=_article_date(article_node),
            publication_types=pub_types,
            mesh_terms=mesh,
            doi=doi,
            pmc_id=pmc,
        ))
    return articles


def _hard_filter(article: Article, request: SearchRequest) -> bool:
    if request.require_abstract and not article.abstract:
        return False
    pubtypes = {value.casefold() for value in article.publication_types}
    if any(value.casefold() in pubtypes for value in request.exclude_publication_types):
        return False
    if request.species:
        mesh = {value.casefold() for value in article.mesh_terms}
        if request.species == "animals" and "animals" not in mesh:
            return False
        if request.species == "humans" and "humans" not in mesh:
            return False
    if article.publication_date:
        year = article.publication_date[:4]
        if request.date_from and year < request.date_from[:4]:
            return False
        if request.date_to and year > request.date_to[:4]:
            return False
    return True


def search_pubmed(request: SearchRequest, retmax: int = 100) -> tuple[str, list[Article]]:
    query = build_pubmed_query(request)
    result = ET.fromstring(_request("esearch.fcgi", {
        "db": "pubmed", "term": query, "retmax": min(max(retmax, 1), 200),
        "retmode": "xml", "sort": "relevance",
    }))
    ids = [node.text for node in result.findall(".//IdList/Id") if node.text]
    if not ids:
        return query, []
    # Stay below the unauthenticated NCBI request rate limit.
    time.sleep(0.34 if not os.getenv("NCBI_API_KEY") else 0.11)
    xml = _request("efetch.fcgi", {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"})
    articles = [article for article in parse_articles(xml) if _hard_filter(article, request)]
    return query, articles
