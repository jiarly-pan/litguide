"""Flask Web 应用 — 文献检索指导系统。"""

from flask import Flask, render_template, request, session, jsonify, redirect, url_for
import secrets

from .models import PaperType, Database
from .keywords import suggest_keywords
from .search_formula import build_all_formulas
from .filter_guide import generate_filter_advice
from .searcher import search_literature
from .session import get_session
from . import history_store


app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

THEMES = ["spring", "aurore", "canele"]


def _parse_type(type_str):
    mapping = {
        "综述型": PaperType.REVIEW, "应用/方法型": PaperType.APPLIED,
        "前沿探索型": PaperType.FRONTIER, "对比分析型": PaperType.COMPARATIVE,
        "review": PaperType.REVIEW, "applied": PaperType.APPLIED,
        "frontier": PaperType.FRONTIER, "comparative": PaperType.COMPARATIVE,
    }
    return mapping.get(type_str, PaperType.REVIEW)


# ==================== 页面路由 ====================

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


@app.route("/history")
def history_page():
    """检索历史页面。"""
    theme = request.args.get("theme", session.get("theme", "spring"))
    if theme not in THEMES:
        theme = "spring"
    session["theme"] = theme
    return render_template("history.html", theme=theme, themes=THEMES)


@app.route("/history/<record_id>")
def history_detail(record_id):
    """检索历史详情页 — 查看某次检索的完整结果。"""
    theme = request.args.get("theme", session.get("theme", "spring"))
    if theme not in THEMES:
        theme = "spring"
    session["theme"] = theme

    record = history_store.get_record(record_id)
    if not record:
        return render_template("history.html", theme=theme, themes=THEMES, error="记录未找到")

    return render_template("history_detail.html", theme=theme, themes=THEMES, record=record)


# ==================== API 路由 ====================

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

    zh_kw, en_kw = suggest_keywords(topic, PaperType.REVIEW)
    keywords_cn = [k.word for k in zh_kw]
    keywords_en = [k.word for k in en_kw]

    if extra_keywords:
        extra = [k.strip() for k in extra_keywords.split() if k.strip()]
        keywords_cn.extend(extra)
        keywords_en.extend(extra)

    all_formulas = build_all_formulas(zh_kw, en_kw)
    formula_cnki = next((f.formula for f in all_formulas if f.database == Database.CNKI), "")
    formula_wos = next((f.formula for f in all_formulas if f.database == Database.WOS), "")

    existing_papers = None
    if is_secondary:
        stored = session.get("last_search_results")
        if stored:
            existing_papers = _deserialize_papers(stored)

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

    session["last_search_results"] = _serialize_papers(results.papers)
    session["last_topic"] = topic

    # 格式化结果
    formatted = _format_results(results)

    # 自动保存到历史记录
    cnki_count = len([p for p in results.papers if p.database == "cnki"])
    wos_count = len([p for p in results.papers if p.database == "wos"])
    cit_count = len([p for p in results.papers if p.is_from_citation])
    record_id = history_store.save_search(
        topic=topic,
        search_query_cnki=formula_cnki,
        search_query_wos=formula_wos,
        total_count=len(results.papers),
        cnki_count=cnki_count,
        wos_count=wos_count,
        citation_count=cit_count,
        is_secondary=is_secondary,
        primary_topic=primary_topic,
        papers=formatted["papers"],
    )
    formatted["record_id"] = record_id

    return jsonify(formatted)


@app.route("/api/history", methods=["GET"])
def api_list_history():
    """获取检索历史列表。"""
    query = request.args.get("q", "").strip()
    if query:
        records = history_store.search_history(query)
    else:
        records = history_store.list_records()
    return jsonify({"records": records, "total": len(records)})


@app.route("/api/history/<record_id>", methods=["GET"])
def api_get_history(record_id):
    """获取单条检索历史详情。"""
    record = history_store.get_record(record_id)
    if not record:
        return jsonify({"error": "记录未找到"}), 404
    return jsonify(record)


@app.route("/api/history/<record_id>", methods=["DELETE"])
def api_delete_history(record_id):
    """删除单条检索历史。"""
    ok = history_store.delete_record(record_id)
    if ok:
        return jsonify({"status": "deleted"})
    return jsonify({"error": "记录未找到"}), 404


@app.route("/api/history/clear", methods=["POST"])
def api_clear_history():
    """清空全部检索历史。"""
    count = history_store.clear_all()
    return jsonify({"status": "cleared", "count": count})


@app.route("/api/switch-theme", methods=["POST"])
def api_switch_theme():
    """切换主题。"""
    data = request.get_json()
    theme = data.get("theme", "spring")
    if theme in THEMES:
        session["theme"] = theme
        return jsonify({"status": "ok", "theme": theme})
    return jsonify({"error": "无效主题"}), 400


# ==================== 辅助函数 ====================

def _serialize_papers(papers):
    return [{
        "title": p.title, "title_zh": p.title_zh, "authors": p.authors,
        "year": p.year, "source": p.source, "citations": p.citations,
        "abstract": p.abstract, "url": p.url, "database": p.database,
        "language": p.language, "doi": p.doi, "keywords": p.keywords,
        "search_query": p.search_query, "is_from_citation": p.is_from_citation,
    } for p in papers]


def _deserialize_papers(data):
    from .models import PaperResult
    return [PaperResult(**d) for d in data]


def _format_results(results):
    papers_json = []
    for p in results.papers:
        papers_json.append({
            "title": p.title, "title_zh": p.title_zh, "authors": p.authors,
            "year": p.year, "source": p.source, "citations": p.citations,
            "abstract": p.abstract, "url": p.url, "database": p.database,
            "language": p.language, "doi": p.doi, "keywords": p.keywords,
            "search_query": p.search_query, "is_from_citation": p.is_from_citation,
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


def main():
    """启动 Flask 开发服务器。"""
    print("文献检索指导系统 Web 版")
    print("访问地址: http://127.0.0.1:5000")
    print("  - 主页 (检索策略):   http://127.0.0.1:5000/")
    print("  - 文献检索:         http://127.0.0.1:5000/literature")
    print("  - 检索历史:         http://127.0.0.1:5000/history")
    app.run(debug=True, host="127.0.0.1", port=5000)


if __name__ == "__main__":
    main()
