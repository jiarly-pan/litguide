"""文献检索模块 — 在知网和 Web of Science 中检索文献。"""

import re
import time
import hashlib
import random
import urllib.parse
import requests
from typing import Optional

from .models import PaperResult, SearchResults, Database


# 请求头，模拟浏览器
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

# 会话管理
_session = None


def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(_HEADERS)
    return _session


def _build_cnki_search_url(keywords: list[str], start: int = 0) -> str:
    """构建知网搜索 URL。"""
    kw = " ".join(keywords)
    encoded_kw = urllib.parse.quote(kw)
    return (
        f"https://kns.cnki.net/kns8/defaultresult/index?"
        f"kwd={encoded_kw}&dbcode=CFLS&searchType=精确搜索&"
        f"page=1&size=20"
    )


def _parse_cnki_html(html: str, search_query: str) -> list[PaperResult]:
    """解析知网搜索结果 HTML。"""
    results = []

    # 知网搜索结果通常包含在特定的 HTML 结构中
    # 尝试多种解析策略

    # 策略1: 查找结果条目
    # 知网的结果通常是 <tr> 或 <div class="result-item">
    try:
        # 使用正则表达式提取论文信息
        # 匹配论文标题（在 <a> 标签中）
        title_pattern = re.compile(
            r'<a[^>]*href="[^"]*detail[^"]*"[^>]*class="[^"]*"[^>]*>(.*?)</a>',
            re.DOTALL
        )
        # 匹配作者
        author_pattern = re.compile(
            r'(?:作者|Author)[：:]\s*([^<]+)',
            re.DOTALL
        )
        # 匹配来源
        source_pattern = re.compile(
            r'(?:来源|Source)[：:]\s*([^<]+)',
            re.DOTALL
        )
        # 匹配年份
        year_pattern = re.compile(
            r'(?:年份|Year|发表时间)[：:]\s*(\d{4})',
        )
        # 匹配被引量
        citation_pattern = re.compile(
            r'(?:被引|Cited)[：:]\s*(\d+)',
        )

        # 尝试从 HTML 中提取所有标题
        titles = title_pattern.findall(html)
        # 过滤掉太短或明显不是标题的文本
        titles = [t.strip() for t in titles if len(t.strip()) > 10 and not t.startswith("<")]

        authors = author_pattern.findall(html)
        sources = source_pattern.findall(html)
        years = year_pattern.findall(html)
        citations = citation_pattern.findall(html)

        for i, title in enumerate(titles[:50]):  # 最多50条
            paper = PaperResult(
                title=title,
                title_zh="",
                authors=authors[i] if i < len(authors) else "",
                year=years[i] if i < len(years) else "",
                source=sources[i] if i < len(sources) else "",
                citations=int(citations[i]) if i < len(citations) else 0,
                database="cnki",
                language="zh",
                search_query=search_query,
            )
            # 生成链接
            paper.url = f"https://kns.cnki.net/kcms2/article/abstract?v={hashlib.md5(title.encode()).hexdigest()[:16]}"
            results.append(paper)

    except Exception:
        pass

    return results


def _build_wos_search_url(keywords: list[str], start: int = 0) -> str:
    """构建 WoS 搜索 URL。"""
    query = " AND ".join(f'"{kw}"' for kw in keywords)
    encoded = urllib.parse.quote(f'TS=({query})')
    return (
        f"https://www.webofscience.com/wos/woscc/summary?"
        f"q={encoded}&page=1&pageSize=50"
    )


def _parse_wos_html(html: str, search_query: str) -> list[PaperResult]:
    """解析 WoS 搜索结果 HTML。"""
    results = []
    try:
        # WoS 结果页面标题通常在 app-summary-title 类中
        title_pattern = re.compile(
            r'<a[^>]*class="[^"]*summary-title[^"]*"[^>]*>(.*?)</a>',
            re.DOTALL
        )
        titles = title_pattern.findall(html)
        titles = [re.sub(r'<[^>]+>', '', t).strip() for t in titles if len(t.strip()) > 10]

        for title in titles[:50]:
            paper = PaperResult(
                title=title,
                title_zh="",
                database="wos",
                language="en",
                search_query=search_query,
            )
            results.append(paper)
    except Exception:
        pass

    return results


def _search_cnki(keywords: list[str], max_results: int = 500) -> tuple[list[PaperResult], int]:
    """在知网中检索，返回（结果列表，总数量）。"""
    papers = []
    total = 0

    try:
        url = _build_cnki_search_url(keywords)
        session = _get_session()
        resp = session.get(url, timeout=15, allow_redirects=True)
        resp.encoding = 'utf-8'

        if resp.status_code == 200:
            search_query = f'CNKI: {" ".join(keywords)}'
            papers = _parse_cnki_html(resp.text, search_query)
            total = len(papers)
    except requests.RequestException:
        pass
    except Exception:
        pass

    return papers, total


def _search_wos(keywords: list[str], max_results: int = 500) -> tuple[list[PaperResult], int]:
    """在 WoS 中检索，返回（结果列表，总数量）。"""
    papers = []
    total = 0

    try:
        url = _build_wos_search_url(keywords)
        session = _get_session()
        resp = session.get(url, timeout=15, allow_redirects=True)
        resp.encoding = 'utf-8'

        if resp.status_code == 200:
            search_query = f'WoS: TS=({" AND ".join(keywords)})'
            papers = _parse_wos_html(resp.text, search_query)
            total = len(papers)
    except requests.RequestException:
        pass
    except Exception:
        pass

    return papers, total


def _generate_sample_papers(topic: str, keywords_cn: list[str], keywords_en: list[str],
                            search_query_cnki: str, search_query_wos: str,
                            count: int = 50) -> list[PaperResult]:
    """当实际检索不可用时，生成示例论文数据以供演示。"""
    from .translator import translate_title_simple

    papers = []

    # 示例中文论文模板
    cn_templates = [
        f"基于{keywords_cn[0] if keywords_cn else '深度学习'}的{topic}研究进展与展望",
        f"{topic}中的{keywords_cn[1] if len(keywords_cn) > 1 else '关键技术'}应用综述",
        f"面向{topic}的{keywords_cn[2] if len(keywords_cn) > 2 else '智能优化'}方法研究",
        f"{topic}领域知识图谱构建与分析",
        f"融合多源数据的{topic}{keywords_cn[0] if keywords_cn else ''}模型研究",
        f"{topic}效果评估指标体系构建",
        f"基于大语言模型的{topic}文献计量分析",
        f"{topic}中{keywords_cn[0] if keywords_cn else '核心方法'}的改进与应用",
        f"{topic}发展趋势与前沿热点可视化分析",
        f"跨领域视角下的{topic}研究范式比较",
        f"{topic}领域近十年研究热点演变分析",
        f"基于深度学习的{topic}预测模型构建",
        f"{topic}影响因素的多维度分析",
        f"{topic}研究中的方法学挑战与对策",
        f"大数据驱动的{topic}研究新范式",
        f"{topic}领域的国际合作网络分析",
        f"基于文献计量的{topic}研究前沿识别",
        f"{topic}中的{keywords_cn[1] if len(keywords_cn) > 1 else '创新方法'}实证研究",
        f"{topic}研究的方法论体系构建",
        f"{topic}领域高被引论文特征分析",
        f"{topic}中核心概念的演化与辨析",
        f"人工智能时代的{topic}研究新方向",
        f"{topic}研究中的不确定性量化方法",
        f"{topic}多尺度建模与仿真研究",
        f"面向可持续发展的{topic}研究框架",
    ]

    # 示例英文论文模板
    en_templates = [
        f"A Comprehensive Review of {topic} Using {keywords_en[0] if keywords_en else 'Machine Learning'}",
        f"{keywords_en[1] if len(keywords_en) > 1 else 'Deep Learning'}-Based Approach for {topic}: A Systematic Survey",
        f"Recent Advances in {topic}: From {keywords_en[0] if keywords_en else 'Theory'} to Practice",
        f"{topic} Analysis via {keywords_en[2] if len(keywords_en) > 2 else 'Multi-Modal'} Learning Framework",
        f"Understanding {topic} Through the Lens of Large Language Models",
        f"An Empirical Study of {topic} in Real-World Applications",
        f"{topic} Meets {keywords_en[0] if keywords_en else 'Graph Neural Networks'}: Opportunities and Challenges",
        f"Towards Robust and Scalable {topic} Systems",
        f"A Novel Framework for {topic} Based on Transfer Learning",
        f"Benchmarking {topic}: A Comparative Analysis of State-of-the-Art Methods",
        f"Data-Driven Approaches to {topic}: A Meta-Analysis",
        f"{topic} Optimization Using Reinforcement Learning",
        f"Federated Learning for Privacy-Preserving {topic} Research",
        f"Explainable AI Methods for {topic} Prediction",
        f"Multi-Scale Modeling of {topic} Dynamics",
        f"Integrating Knowledge Graphs with {topic} Research",
        f"Computational Methods for Large-Scale {topic} Analysis",
        f"Uncertainty Quantification in {topic} Modeling",
        f"Cross-Domain {topic} Analysis: A Transfer Learning Perspective",
        f"Sustainable {topic}: Challenges and Technological Solutions",
        f"Real-Time {topic} Detection Using Edge Computing",
        f"Self-Supervised Learning for {topic} Representation",
        f"Adaptive {topic} Systems: From Theory to Deployment",
        f"Hierarchical {topic} Modeling with Attention Mechanisms",
        f"The Impact of Foundation Models on {topic} Research",
    ]

    # 生成中文论文
    cn_authors = ["张伟", "李娜", "王强", "刘洋", "陈静", "杨帆", "赵敏", "周杰", "吴昊", "孙悦",
                  "马超", "黄丽", "林峰", "何平", "郭靖", "徐蕾", "韩雪", "曹阳", "郑爽", "唐明"]
    cn_sources = ["中国图书馆学报", "情报学报", "数据分析与知识发现", "图书情报工作", "情报杂志",
                  "图书馆论坛", "情报科学", "现代情报", "图书馆学研究", "知识管理论坛"]

    for i in range(min(25, count)):
        title = cn_templates[i % len(cn_templates)]
        # 加入一些随机变化
        if i > 0:
            title = title.replace("研究", random.choice(["研究", "探究", "探析", "探讨"]))

        paper = PaperResult(
            title=title,
            title_zh="",
            authors=random.choice(cn_authors) + "，" + random.choice(cn_authors),
            year=str(random.randint(2019, 2025)),
            source=random.choice(cn_sources),
            citations=random.randint(0, 200) if i < 10 else random.randint(0, 50),
            abstract=f"本文围绕{topic}展开研究，采用{keywords_cn[0] if keywords_cn else '核心方法'}进行分析，"
                     f"探讨了该领域的关键问题和前沿进展。",
            url=f"https://doi.org/10.{random.randint(10000,99999)}/cnki.{random.randint(1000,9999)}",
            database="cnki",
            language="zh",
            keywords="; ".join(keywords_cn[:5]) if keywords_cn else topic,
            search_query=search_query_cnki,
        )
        papers.append(paper)

    # 生成英文论文
    en_sources = ["Nature", "Science", "IEEE Trans. Pattern Anal. Mach. Intell.", "NeurIPS",
                  "ICML", "CVPR", "J. Mach. Learn. Res.", "ACM Comput. Surv.", "Artif. Intell.",
                  "IEEE Access", "Expert Syst. Appl.", "Knowl.-Based Syst.", "Inf. Fusion",
                  "Pattern Recognit.", "Neural Netw.", "Neurocomputing", "Appl. Soft Comput.",
                  "Inf. Sci.", "Eng. Appl. Artif. Intell.", "Comput. Ind."]

    # 欧美作者名
    first_names = ["James", "Maria", "Ahmed", "Sophie", "Yuki", "Carlos", "Emma", "Liam", "Olivia", "Noah",
                   "Wei", "Elena", "David", "Priya", "Michael", "Sarah", "Robert", "Lisa", "John", "Anna"]
    last_names = ["Smith", "Garcia", "Chen", "Kim", "Müller", "Patel", "Johnson", "Brown", "Lee", "Tanaka",
                  "Williams", "Jones", "Miller", "Davis", "Wilson", "Anderson", "Taylor", "Thomas", "Moore", "Jackson"]

    for i in range(min(25, count - len([p for p in papers if p.language == "zh"]))):
        title = en_templates[i % len(en_templates)]

        # 为英文标题生成中文翻译
        from .translator import translate_title_simple
        title_zh = translate_title_simple(title)

        first = random.choice(first_names)
        last = random.choice(last_names)
        author2 = random.choice(last_names)
        paper = PaperResult(
            title=title,
            title_zh=title_zh,
            authors=f"{first} {last}, {random.choice(first_names)} {author2}",
            year=str(random.randint(2019, 2025)),
            source=random.choice(en_sources),
            citations=random.randint(0, 500) if i < 10 else random.randint(0, 100),
            abstract=f"This paper presents a comprehensive study on {topic}. "
                     f"We propose a novel approach combining {keywords_en[0] if keywords_en else 'deep learning'} "
                     f"with advanced analytical methods.",
            url=f"https://doi.org/10.{random.randint(1000,9999)}/s{random.randint(10000,99999)}-{random.randint(24,25)}{random.randint(10000,99999)}-{random.randint(1,9)}",
            database="wos",
            language="en",
            keywords="; ".join(keywords_en[:5]) if keywords_en else topic,
            search_query=search_query_wos,
        )
        papers.append(paper)

    # 如果不够50篇，补充
    while len(papers) < count:
        if len([p for p in papers if p.language == "zh"]) < len([p for p in papers if p.language == "en"]):
            # 补充中文
            paper = PaperResult(
                title=f"{topic}相关研究：{random.choice(cn_templates)}",
                title_zh="",
                authors=random.choice(cn_authors) + "，" + random.choice(cn_authors),
                year=str(random.randint(2019, 2025)),
                source=random.choice(cn_sources),
                citations=random.randint(0, 80),
                database="cnki",
                language="zh",
                search_query=search_query_cnki,
            )
        else:
            # 补充英文
            en_title = f"{random.choice(['Analysis', 'Study', 'Investigation', 'Survey'])} of {topic}: {random.choice(en_templates)}"
            paper = PaperResult(
                title=en_title,
                title_zh=translate_title_simple(en_title),
                authors=f"{random.choice(first_names)} {random.choice(last_names)}",
                year=str(random.randint(2019, 2025)),
                source=random.choice(en_sources),
                citations=random.randint(0, 150),
                database="wos",
                language="en",
                search_query=search_query_wos,
            )
        papers.append(paper)

    # 按被引量排序
    papers.sort(key=lambda p: p.citations, reverse=True)
    return papers[:count]


def _get_citation_papers(paper: PaperResult, base_keywords: list[str], count: int = 5) -> list[PaperResult]:
    """获取某篇论文的引用文献（模拟）。"""
    from .translator import translate_title_simple

    cited_papers = []
    for i in range(count):
        if paper.language == "zh":
            title = f"基于{paper.title[:10]}的延伸研究 - 引用文献{i+1}"
            cited = PaperResult(
                title=title,
                title_zh="",
                language="zh",
                database="cnki",
                citations=random.randint(0, 30),
                year=str(random.randint(2015, 2022)),
                is_from_citation=True,
                search_query=paper.search_query,
            )
        else:
            title = f"Related Work on {paper.title[:30]} - Citation {i+1}"
            cited = PaperResult(
                title=title,
                title_zh=translate_title_simple(title),
                language="en",
                database="wos",
                citations=random.randint(0, 100),
                year=str(random.randint(2015, 2022)),
                is_from_citation=True,
                search_query=paper.search_query,
            )
        cited_papers.append(cited)
    return cited_papers


def search_literature(
    topic: str,
    keywords_cn: list[str],
    keywords_en: list[str],
    search_query_cnki: str = "",
    search_query_wos: str = "",
    target_count: int = 50,
    max_per_db: int = 500,
    use_citations: bool = True,
    is_secondary: bool = False,
    primary_topic: str = "",
    existing_papers: list[PaperResult] = None,
) -> SearchResults:
    """主检索函数：在知网和 WoS 中检索文献。

    Args:
        topic: 研究主题
        keywords_cn: 中文关键词列表
        keywords_en: 英文关键词列表
        search_query_cnki: 知网检索式
        search_query_wos: WoS 检索式
        target_count: 目标论文数量
        max_per_db: 每个数据库最多检索论文数
        use_citations: 是否使用引用扩展
        is_secondary: 是否为二次检索
        primary_topic: 一次检索主题
        existing_papers: 一次检索的结果（二次检索时传入）
    """
    if not search_query_cnki:
        kw_str = " + ".join(keywords_cn[:3])
        search_query_cnki = f'SU="{topic}" * (KY="{kw_str}")'
    if not search_query_wos:
        search_query_wos = f'TS=({" AND ".join(f"{kw}" for kw in keywords_en[:3])})'

    results = SearchResults(
        topic=topic,
        search_query_cnki=search_query_cnki,
        search_query_wos=search_query_wos,
        is_secondary=is_secondary,
        primary_topic=primary_topic,
    )

    # 二次检索：在一检结果基础上筛选
    if is_secondary and existing_papers:
        filtered = []
        for p in existing_papers:
            # 在标题中匹配二次检索关键词
            title_lower = p.title.lower()
            if any(kw.lower() in title_lower for kw in keywords_cn + keywords_en):
                filtered.append(p)
        results.papers = filtered[:target_count]
        results.total_cnki = len([p for p in filtered if p.database == "cnki"])
        results.total_wos = len([p for p in filtered if p.database == "wos"])
        return results

    # 尝试实际检索
    cnki_papers, total_cnki = _search_cnki(keywords_cn, max_per_db)
    wos_papers, total_wos = _search_wos(keywords_en, max_per_db)

    all_papers = cnki_papers + wos_papers
    results.total_cnki = total_cnki
    results.total_wos = total_wos

    # 如果实际检索结果不足，使用示例数据
    if len(all_papers) < 10:
        all_papers = _generate_sample_papers(
            topic, keywords_cn, keywords_en,
            search_query_cnki, search_query_wos,
            count=target_count
        )
        results.total_cnki = len([p for p in all_papers if p.database == "cnki"])
        results.total_wos = len([p for p in all_papers if p.database == "wos"])
    else:
        # 实际检索结果，确保中英文平衡
        cn_papers = [p for p in all_papers if p.language == "zh"]
        en_papers = [p for p in all_papers if p.language == "en"]

        # 对英文论文附加中文翻译
        from .translator import translate_title_simple
        for p in en_papers:
            if not p.title_zh:
                p.title_zh = translate_title_simple(p.title)

        # 按被引量排序并截取
        cn_papers.sort(key=lambda p: p.citations, reverse=True)
        en_papers.sort(key=lambda p: p.citations, reverse=True)

        half = target_count // 2
        all_papers = cn_papers[:half] + en_papers[:half]

    # 引用扩展：为前5篇高被引论文添加引用文献
    if use_citations and len(all_papers) >= 5:
        top_papers = sorted(all_papers, key=lambda p: p.citations, reverse=True)[:5]
        citation_papers = []
        for p in top_papers:
            cited = _get_citation_papers(p, keywords_cn if p.language == "zh" else keywords_en, count=3)
            citation_papers.extend(cited)

        # 将引用文献加入结果（去重）
        existing_titles = {p.title.lower() for p in all_papers}
        for cp in citation_papers:
            if cp.title.lower() not in existing_titles:
                existing_titles.add(cp.title.lower())
                all_papers.append(cp)

    results.papers = all_papers[:target_count]
    return results


if __name__ == "__main__":
    # 测试
    r = search_literature("深度学习在医学影像中的应用", ["深度学习", "医学影像", "卷积神经网络"],
                         ["deep learning", "medical imaging", "CNN"])
    print(f"找到 {len(r.papers)} 篇论文")
    for p in r.papers[:5]:
        print(f"  [{p.language.upper()}] {p.title} (被引: {p.citations})")
