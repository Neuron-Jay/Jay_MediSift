"""Streamlit interface for natural-language PubMed search."""

import streamlit as st

from pubmed.download import download_article
from pubmed.llm import interpret_request
from pubmed.models import Article, RankedArticle, SearchRequest
from pubmed.ranking import rank_articles
from pubmed.search import search_pubmed


st.set_page_config(page_title="MediSift · PubMed", page_icon="📚", layout="wide")

st.title("📚 MediSift PubMed 文献检索")
st.caption("用自然语言描述研究问题。AI 帮你检索和排序，最后由你选择要保存的文献。")

with st.sidebar:
    st.subheader("使用说明")
    st.markdown(
        """
1. 描述主题、时间范围和研究类型
2. 查看检索条件与相关性排序
3. 勾选想保留的记录并保存

保存的题录和摘要会写入 `text_file_repository`，可继续用 `deep_agent.py` 分析。
        """
    )
    st.caption("需要在项目根目录 `.env` 中配置 `DEEPSEEK_API_KEY`。")
    st.caption("排序用于辅助筛选；请根据原文和研究判断自行选择。")


def _search_request(text: str) -> tuple[SearchRequest, str, list[Article]]:
    parsed = interpret_request(text)
    request = SearchRequest.from_dict(parsed, text)
    if not request.concepts:
        raise ValueError("没有解析出检索主题。请补充疾病、研究对象或核心概念后重试。")
    query, articles = search_pubmed(request)
    return request, query, articles


def _show_search_request(request: SearchRequest) -> None:
    st.subheader("检索条件")
    cols = st.columns(2)
    with cols[0]:
        for index, concept in enumerate(request.concepts, 1):
            terms = concept.get("terms", []) + concept.get("mesh_terms", [])
            st.markdown(f"**主题 {index}：** " + (" · ".join(terms) or "未识别"))
        if request.study_types:
            st.markdown("**研究类型：** " + " · ".join(request.study_types))
    with cols[1]:
        if request.species:
            st.markdown(f"**物种：** {request.species}")
        if request.date_from or request.date_to:
            st.markdown(f"**日期：** {request.date_from or '不限'} 至 {request.date_to or '不限'}")
        if request.publication_types:
            st.markdown("**出版类型：** " + " · ".join(request.publication_types))
        if request.exclude_publication_types:
            st.markdown("**排除：** " + " · ".join(request.exclude_publication_types))


def _show_result(index: int, result: RankedArticle) -> None:
    article = result.article
    key = f"pubmed_selected_{article.pmid}"
    st.checkbox(f"{index}. {article.title}", key=key)
    st.markdown(
        f"**{result.relevance}** · {article.publication_date[:4] or '日期未知'} · "
        f"{article.journal or '期刊未知'} · PMID {article.pmid}"
    )
    st.write(f"AI 理由：{result.reason}")
    st.markdown(f"[打开 PubMed 记录]({article.pubmed_url})")
    if article.abstract:
        with st.expander("查看摘要"):
            st.write(article.abstract)
    st.divider()


if "pubmed_results" not in st.session_state:
    st.session_state.pubmed_results = []
if "pubmed_search_request" not in st.session_state:
    st.session_state.pubmed_search_request = None

with st.form("pubmed_search_form"):
    user_query = st.text_area(
        "你想找什么文献？",
        value="近五年关于帕金森病和脑膜淋巴管关系的动物实验研究，不要综述。",
        height=110,
        placeholder="例如：近五年关于帕金森病和脑膜淋巴管关系的动物实验研究，不要综述。",
    )
    submitted = st.form_submit_button("🔎 搜索 PubMed", type="primary", use_container_width=True)

if submitted:
    if not user_query.strip():
        st.warning("请先描述你的检索需求。")
    else:
        # Clear selection state from the prior search before replacing its results.
        for old_result in st.session_state.pubmed_results:
            st.session_state.pop(f"pubmed_selected_{old_result.article.pmid}", None)
        st.session_state.pubmed_results = []
        st.session_state.pubmed_search_request = None
        try:
            with st.spinner("AI 正在理解需求并检索 PubMed…"):
                request, query, articles = _search_request(user_query.strip())
            st.session_state.pubmed_search_request = request
            st.session_state.pubmed_query = query
            st.session_state.pubmed_candidate_count = len(articles)
            if articles:
                with st.spinner(f"正在对 {min(len(articles), 50)} 篇候选文献进行相关性排序…"):
                    st.session_state.pubmed_results = rank_articles(request, articles, limit=50)[:30]
        except Exception as exc:
            st.error(f"检索失败：{exc}")

request = st.session_state.pubmed_search_request
results: list[RankedArticle] = st.session_state.pubmed_results
if request is not None:
    st.divider()
    _show_search_request(request)
    st.caption(f"PubMed 返回并通过硬过滤：{st.session_state.get('pubmed_candidate_count', 0)} 篇候选。")
    with st.expander("查看生成的 PubMed Query"):
        st.code(st.session_state.get("pubmed_query", ""), language="text")

    if not results:
        st.info("没有找到符合条件的文献。你可以调整上方的自然语言描述后重新搜索。")
    else:
        st.subheader(f"相关性排序 · 展示 {len(results)} 篇")
        st.caption("勾选标题以选择记录；不会在搜索后自动保存或分析文献。")
        for index, result in enumerate(results, 1):
            _show_result(index, result)

        selected = [
            result.article
            for result in results
            if st.session_state.get(f"pubmed_selected_{result.article.pmid}", False)
        ]
        st.write(f"已选择 **{len(selected)}** 篇")
        if st.button("💾 保存选中文献", type="primary", disabled=not selected):
            saved = 0
            for article in selected:
                try:
                    path = download_article(article)
                    st.success(f"已保存：{path}")
                    saved += 1
                except Exception as exc:
                    st.error(f"保存 PMID {article.pmid} 失败：{exc}")
            if saved:
                st.info("保存的是题录和摘要，可在 `text_file_repository` 中查看并交给 deep_agent.py 分析。")
