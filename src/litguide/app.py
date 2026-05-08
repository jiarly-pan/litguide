"""Flask Web 应用 — 文献检索指导系统。"""

from flask import Flask, render_template, request, session, jsonify, redirect, url_for
import secrets

from .models import PaperType, Database
from .keywords import suggest_keywords
from .search_formula import build_all_formulas
from .filter_guide import generate_filter_advice
from .searcher import search_literature
from .session import get_session


app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# 主题列表
THEMES = ["spring", "aurore", "canele"]


def _parse_type(type_str):
    mapping = {
        "综述型": PaperType.REVIEW, "应用/方法型": PaperType.APPLIED,
        "前沿探索型": PaperType.FRONTIER, "对比分析型": PaperType.COMPARATIVE,
        "review": PaperType.REVIEW, "applied": PaperType.APPLIED,
        "frontier": PaperType.FRONTIER, "comparative": PaperType.COMPARATIVE,
    }
    return mapping.get(type_str, PaperType.REVIEW)


@app.route("/")
def index():
    """主页 — 检索策略生成（原有功能）。"""
    theme = request.args.get("theme", session.get("theme", "spring"))
    if theme not in THEMES:
        theme = "spring"
    session["theme"] = theme
    return render_template("index.html", theme=theme, themes=THEMES)


@app.route("/literature")
def literature():
    """文献检索页面（新功能）。"""
    theme = request.args.get("theme", session.get("theme", "spring"))
    if theme not in THEMES:
        theme = "spring"
    session["theme"] = theme
    return render_template("search.html", theme=theme, themes=THEMES)


@app.route("/api/search-guidance", methods=["POST"])
def api_search_guidance():
    """生成检索策略 API（原有功能）。"""
    data = request.get_json()
    topic = data.get("topic", "").strip()
    paper_type_str = data.get("paper_type", "综述型")

    if not topic:
        return jsonify({"error": "请输入研究主题"}), 400

    pt = _parse_type(paper_type_str)
    zh_kw, en_kw = suggest_keywords(topic, pt)
    formulas = build_all_formulas(zh_kw, en_kw)
    advice = generate_filter_advice(pt)

    # 转化为可序列化的格式
    result = {
        "topic": topic,
        "paper_type": pt.value,
        "keywords_zh": [{"word": k.word, "is_primary": k.is_primary, "rationale": k.rationale}
                        for k in zh_kw],
        "keywords_en": [{"word": k.word, "is_primary": k.is_primary, "rationale": k.rationale}
                        for k in en_kw],
        "formulas": [{"database": f.database.label, "language": f.database.language,
                       "formula": f.formula, "note": f.note}
                      for f in formulas],
        "filter_advice": {
            "weights": advice.weights,
            "year_strategy": advice.year_strategy,
            "source_strategy": advice.source_strategy,
            "tips": advice.tips,
        },
    }

    # 记录到会话
    sess = get_session()
    all_kw = [k.word for k in zh_kw + en_kw]
    sess.record_search(topic, pt.value, all_kw)

    return jsonify(result)


@app.route("/api/search-literature", methods=["POST"])
def api_search_literature():
    """执行文献检索 API。"""
    data = request.get_json()
    topic = data.get("topic", "").strip()
    is_secondary = data.get("is_secondary", False)
    primary_topic = data.get("primary_topic", "")
    use_citations = data.get("use_citations", True)
    extra_keywords = data.get("extra_keywords", "").strip()

    if not topic:
        return jsonify({"error": "请输入研究主题"}), 400

    # 生成关键词
    zh_kw, en_kw = suggest_keywords(topic, PaperType.REVIEW)
    keywords_cn = [k.word for k in zh_kw]
    keywords_en = [k.word for k in en_kw]

    # 如果有额外关键词（二次检索）
    if extra_keywords:
        extra = [k.strip() for k in extra_keywords.split() if k.strip()]
        keywords_cn.extend(extra)
        keywords_en.extend(extra)

    # 生成检索式
    from .search_formula import build_all_formulas
    all_formulas = build_all_formulas(zh_kw, en_kw)
    formula_cnki = next((f.formula for f in all_formulas if f.database == Database.CNKI), "")
    formula_wos = next((f.formula for f in all_formulas if f.database == Database.WOS), "")

    # 二次检索：从 session 获取一检结果
    existing_papers = None
    if is_secondary:
        stored = session.get("last_search_results")
        if stored:
            existing_papers = _deserialize_papers(stored)

    # 执行检索
    results = search_literature(
        topic=topic,
        keywords_cn=keywords_cn,
        keywords_en=keywords_en,
        search_query_cnki=formula_cnki,
        search_query_wos=formula_wos,
        target_count=50,
        max_per_db=500,
        use_citations=use_citations,
        is_secondary=is_secondary,
        primary_topic=primary_topic,
        existing_papers=existing_papers,
    )

    # 将结果存入 session 以便二次检索
    session["last_search_results"] = _serialize_papers(results.papers)
    session["last_topic"] = topic

    return jsonify(_format_results(results))


def _serialize_papers(papers):
    """将论文列表序列化为可存储的字典列表。"""
    return [{
        "title": p.title,
        "title_zh": p.title_zh,
        "authors": p.authors,
        "year": p.year,
        "source": p.source,
        "citations": p.citations,
        "abstract": p.abstract,
        "url": p.url,
        "database": p.database,
        "language": p.language,
        "doi": p.doi,
        "keywords": p.keywords,
        "search_query": p.search_query,
        "is_from_citation": p.is_from_citation,
    } for p in papers]


def _deserialize_papers(data):
    """从字典列表反序列化论文。"""
    from .models import PaperResult
    return [PaperResult(**d) for d in data]


def _format_results(results):
    """格式化检索结果为 JSON。"""
    papers_json = []
    for p in results.papers:
        papers_json.append({
            "title": p.title,
            "title_zh": p.title_zh,
            "authors": p.authors,
            "year": p.year,
            "source": p.source,
            "citations": p.citations,
            "abstract": p.abstract,
            "url": p.url,
            "database": p.database,
            "language": p.language,
            "doi": p.doi,
            "keywords": p.keywords,
            "search_query": p.search_query,
            "is_from_citation": p.is_from_citation,
        })

    return {
        "topic": results.topic,
        "search_query_cnki": results.search_query_cnki,
        "search_query_wos": results.search_query_wos,
        "total_cnki": results.total_cnki,
        "total_wos": results.total_wos,
        "total_count": len(results.papers),
        "is_secondary": results.is_secondary,
        "primary_topic": results.primary_topic,
        "papers": papers_json,
    }


@app.route("/api/switch-theme", methods=["POST"])
def api_switch_theme():
    """切换主题。"""
    data = request.get_json()
    theme = data.get("theme", "spring")
    if theme in THEMES:
        session["theme"] = theme
        return jsonify({"status": "ok", "theme": theme})
    return jsonify({"error": "无效主题"}), 400


def main():
    """启动 Flask 开发服务器。"""
    print("文献检索指导系统 Web 版")
    print("访问地址: http://127.0.0.1:5000")
    print("  - 主页 (检索策略): http://127.0.0.1:5000/")
    print("  - 文献检索: http://127.0.0.1:5000/literature")
    app.run(debug=True, host="127.0.0.1", port=5000)


if __name__ == "__main__":
    main()
