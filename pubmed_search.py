"""Interactive natural-language PubMed search and user-selected saving."""

from pubmed.download import download_article
from pubmed.llm import interpret_request
from pubmed.models import RankedArticle, SearchRequest
from pubmed.ranking import rank_articles
from pubmed.search import search_pubmed


def _display_request(request: SearchRequest) -> None:
    print("\nMediSift 理解的检索条件：")
    for concept in request.concepts:
        print("  • " + " / ".join(concept.get("terms", []) + concept.get("mesh_terms", [])))
    if request.study_types:
        print("  • 研究类型：" + " / ".join(request.study_types))
    if request.species:
        print("  • 物种：" + request.species)
    if request.date_from or request.date_to:
        print(f"  • 日期：{request.date_from or '最早'} 至 {request.date_to or '最新'}")
    if request.exclude_publication_types:
        print("  • 排除：" + " / ".join(request.exclude_publication_types))


def _show_results(results: list[RankedArticle]) -> None:
    previous = None
    for index, item in enumerate(results, 1):
        if item.relevance != previous:
            print(f"\n--- {item.relevance} ---")
            previous = item.relevance
        article = item.article
        print(f"\n{index}. {article.title}")
        print(f"   {article.publication_date[:4] or '日期未知'} · {article.journal or '期刊未知'} · PMID {article.pmid}")
        print(f"   AI：{item.reason}")
        print(f"   {article.pubmed_url}")


def _selection(value: str, count: int) -> list[int]:
    selected = set()
    for chunk in value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start, end = (int(part.strip()) for part in chunk.split("-", 1))
            selected.update(range(start, end + 1))
        else:
            selected.add(int(chunk))
    if any(index < 1 or index > count for index in selected):
        raise ValueError
    return sorted(selected)


def main() -> None:
    text = input("请描述你想检索的 PubMed 文献：\n> ").strip()
    if not text:
        print("检索需求不能为空。")
        return
    try:
        request = SearchRequest.from_dict(interpret_request(text), text)
        if not request.concepts:
            raise ValueError("没有解析出检索主题，请换一种方式描述。")
        _display_request(request)
        query, articles = search_pubmed(request)
        print(f"\nPubMed 检索完成：原始候选 {len(articles)} 篇。")
        if not articles:
            print("没有找到符合条件的记录。可以修改描述后重试。")
            return
        print("正在进行 AI 相关性排序……")
        results = rank_articles(request, articles, limit=50)
        results = results[:30]
        _show_results(results)
        print(f"\nPubMed Query：{query}")
        answer = input("\n选择要保存的文献（如 1,3,5-7；直接回车退出）：").strip()
        if not answer:
            return
        try:
            indexes = _selection(answer, len(results))
        except (ValueError, TypeError):
            print("选择格式无效或序号超出范围，没有保存文件。")
            return
        for index in indexes:
            article = results[index - 1].article
            record_path = download_article(article)
            print(f"已保存题录和摘要：{record_path}")
        print("记录保存在 text_file_repository，可继续使用 deep_agent.py 分析；全文请通过记录中的 PubMed/PMC 链接查看或获取。")
    except Exception as exc:
        print(f"检索失败：{exc}")


if __name__ == "__main__":
    main()
