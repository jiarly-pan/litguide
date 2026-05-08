"""数据模型：文献类型、数据库、检索请求与结果。"""

from dataclasses import dataclass, field
from enum import Enum


class PaperType(Enum):
    """文献类型枚举"""
    REVIEW = "综述型"
    APPLIED = "应用/方法型"
    FRONTIER = "前沿探索型"
    COMPARATIVE = "对比分析型"

    def __str__(self):
        return self.value


class Database(Enum):
    """支持的学术数据库"""
    CNKI = ("知网 CNKI", "中文")
    WOS = ("Web of Science", "英文")
    SEMANTIC_SCHOLAR = ("Semantic Scholar", "英文")
    CROSSREF = ("Crossref", "英文")

    def __init__(self, label, language):
        self.label = label
        self.language = language


# 权重配置表
WEIGHT_TABLE = {
    PaperType.REVIEW:       {"relevance": 40, "citations": 35, "recency": 25},
    PaperType.APPLIED:      {"relevance": 50, "citations": 20, "recency": 30},
    PaperType.FRONTIER:     {"relevance": 30, "citations": 15, "recency": 55},
    PaperType.COMPARATIVE:  {"relevance": 45, "citations": 30, "recency": 25},
}

# 年份策略配置表
YEAR_STRATEGY = {
    PaperType.REVIEW:       "经典文献 + 近5年",
    PaperType.APPLIED:      "近3-5年",
    PaperType.FRONTIER:     "近1-2年",
    PaperType.COMPARATIVE:  "宽年份跨度",
}

# 来源推荐配置表
SOURCE_STRATEGY = {
    PaperType.REVIEW:       "高影响力综述期刊（如 Nature Reviews、CSSCI 综述期刊）",
    PaperType.APPLIED:      "技术报告、方法论论文、案例研究（如 arXiv、会议论文）",
    PaperType.FRONTIER:     "预印本（arXiv、TechRxiv）、顶级会议论文",
    PaperType.COMPARATIVE:  "多来源数据库交叉检索、跨领域高被引文献",
}

# 数据库检索语法模板
DB_SYNTAX = {
    Database.CNKI:              'SU="{核心词}" * (KY="{词1}" + KY="{词2}")',
    Database.WOS:               'TS=("{keyword1}" AND "{keyword2}")',
    Database.SEMANTIC_SCHOLAR:  '自然语言搜索 + 领域过滤器',
    Database.CROSSREF:          '/works?query={keyword1}+{keyword2}&filter=type:journal-article',
}


@dataclass
class KeywordEntry:
    """检索词条目"""
    word: str
    language: str       # "zh" | "en"
    is_primary: bool    # True = 主关键词 ★
    rationale: str = "" # 推荐理由


@dataclass
class SearchFormula:
    """检索式"""
    database: Database
    formula: str
    note: str = ""


@dataclass
class FilterAdvice:
    """筛选建议"""
    paper_type: PaperType
    weights: dict          # {"relevance": 40, "citations": 35, "recency": 25}
    year_strategy: str
    source_strategy: str
    tips: list[str] = field(default_factory=list)


@dataclass
class SearchGuidance:
    """一次完整的检索指导输出"""
    topic: str                          # 用户研究方向
    paper_type: PaperType                # 文献类型
    keywords_zh: list[KeywordEntry]      # 中文检索词
    keywords_en: list[KeywordEntry]      # 英文检索词
    formulas: list[SearchFormula]        # 各数据库检索式
    filter_advice: FilterAdvice          # 筛选建议
