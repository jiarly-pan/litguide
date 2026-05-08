"""筛选指导生成器 — 根据文献类型输出筛选策略与权重建议。"""

from .models import PaperType, FilterAdvice, WEIGHT_TABLE, YEAR_STRATEGY, SOURCE_STRATEGY


def generate_filter_advice(paper_type: PaperType) -> FilterAdvice:
    """根据文献类型生成筛选建议。"""
    weights = WEIGHT_TABLE[paper_type]
    year_strategy = YEAR_STRATEGY[paper_type]
    source_strategy = SOURCE_STRATEGY[paper_type]

    tips = _generate_tips(paper_type, weights)

    return FilterAdvice(
        paper_type=paper_type,
        weights=weights,
        year_strategy=year_strategy,
        source_strategy=source_strategy,
        tips=tips,
    )


def _generate_tips(paper_type: PaperType, weights: dict) -> list[str]:
    """生成具体的筛选操作建议。"""
    tips = []

    tips.append(f"排序优先级：相关性({weights['relevance']}%) > 引用量({weights['citations']}%) > 时效性({weights['recency']}%)")

    if paper_type == PaperType.REVIEW:
        tips.append("优先选择发表在高影响力综述期刊上的文章（如 Annual Review 系列、Nature Reviews 系列）")
        tips.append("兼顾里程碑式经典文献（可能发表于10年前）和近5年的最新综述")
        tips.append("尤其关注文中引用量 > 100 的高被引综述，可作为该领域的入门文献")

    elif paper_type == PaperType.APPLIED:
        tips.append("优先选择有完整实验流程、可复现方法描述的论文")
        tips.append("关注论文的「方法」和「实验」章节是否详尽，筛除纯理论推导文献")
        tips.append("近3-5年内发表的技术报告和会议论文更可能反映当前最佳实践")

    elif paper_type == PaperType.FRONTIER:
        tips.append("优先检索预印本平台（arXiv、TechRxiv）和近期顶级会议论文")
        tips.append("时效性权重最高(55%)，重点筛选近1-2年内的文献")
        tips.append("关注被引量上升趋势而非绝对值（新论文引用量必然较低）")
        tips.append("建议设置 Google Scholar 或 Semantic Scholar 的邮件提醒，持续追踪最新进展")

    elif paper_type == PaperType.COMPARATIVE:
        tips.append("在多个数据库中交叉检索，确保覆盖不同领域的相关文献")
        tips.append("优先选择同时包含多领域对比数据的综述或元分析论文")
        tips.append("注意检索式的多样性——同一概念在不同领域可能有不同的术语表达")
        tips.append("建议使用引文追溯法：从一篇核心对比文献出发，追溯其参考文献和后续引用者")

    return tips
