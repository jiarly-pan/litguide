"""检索式生成器 — 根据检索词生成各数据库适用的检索式。"""

from .models import Database, SearchFormula, KeywordEntry, DB_SYNTAX


def _pick_keywords(keywords: list[KeywordEntry], count: int = 3) -> list[str]:
    """从关键词列表中挑选，主关键词优先。"""
    primary = [k.word for k in keywords if k.is_primary]
    secondary = [k.word for k in keywords if not k.is_primary]
    return (primary + secondary)[:count]


def build_formula_cnki(keywords: list[KeywordEntry]) -> SearchFormula:
    """构建 CNKI 检索式。"""
    picked = _pick_keywords(keywords, 4)
    core = picked[0] if picked else "关键词"
    others = " + ".join(f"KY='{w}'" for w in picked[1:]) if len(picked) > 1 else ""
    if others:
        formula = f'SU="{core}" * ({others})'
    else:
        formula = f'SU="{core}"'
    return SearchFormula(
        database=Database.CNKI,
        formula=formula,
        note="知网专业检索模式，SU=主题，KY=关键词，*=逻辑与，+=逻辑或",
    )


def build_formula_wos(keywords: list[KeywordEntry]) -> SearchFormula:
    """构建 Web of Science 检索式。"""
    picked = _pick_keywords(keywords, 4)
    parts = " AND ".join(f'"{w}"' for w in picked)
    formula = f'TS=({parts})'
    return SearchFormula(
        database=Database.WOS,
        formula=formula,
        note="WoS 高级检索，TS=Topic（标题+摘要+关键词），AND 缩小范围",
    )


def build_formula_semantic_scholar(keywords: list[KeywordEntry]) -> SearchFormula:
    """构建 Semantic Scholar 检索指导。"""
    picked = _pick_keywords(keywords, 3)
    return SearchFormula(
        database=Database.SEMANTIC_SCHOLAR,
        formula=f'{" ".join(picked)}',
        note="Semantic Scholar 支持自然语言搜索，可直接输入关键词组合，然后用左侧过滤器限定年份和领域",
    )


def build_formula_crossref(keywords: list[KeywordEntry]) -> SearchFormula:
    """构建 Crossref 检索式。"""
    picked = _pick_keywords(keywords, 3)
    formula = f'/works?query={"+".join(picked)}&filter=type:journal-article&rows=50'
    return SearchFormula(
        database=Database.CROSSREF,
        formula=formula,
        note="Crossref REST API，免费无需 Key，返回 DOI + 元数据，可通过 filter 限定文献类型",
    )


# 构建器注册表
_BUILDERS = {
    Database.CNKI: build_formula_cnki,
    Database.WOS: build_formula_wos,
    Database.SEMANTIC_SCHOLAR: build_formula_semantic_scholar,
    Database.CROSSREF: build_formula_crossref,
}


def build_all_formulas(zh_keywords: list[KeywordEntry], en_keywords: list[KeywordEntry]) -> list[SearchFormula]:
    """为所有目标数据库生成检索式。"""
    formulas = []
    for db, builder in _BUILDERS.items():
        # 根据数据库语言选择对应的关键词
        if db.language == "中文":
            kw = zh_keywords
        else:
            kw = en_keywords
        formulas.append(builder(kw))
    return formulas
