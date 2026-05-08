"""数据模型：文献类型、数据库、检索请求与结果。"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


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
}


@dataclass
class KeywordEntry:
    """检索词条目"""
    word: str
    language: str       # "zh" | "en"
    is_primary: bool    # True = 主关键词 ★
    rationale: str = ""  # 推荐理由


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
    topic: str
    paper_type: PaperType
    keywords_zh: list[KeywordEntry]
    keywords_en: list[KeywordEntry]
    formulas: list[SearchFormula]
    filter_advice: FilterAdvice


@dataclass
class PaperResult:
    """单篇论文检索结果"""
    title: str                  # 论文标题（英文论文保留英文标题）
    title_zh: str = ""          # 英文论文的中文翻译标题
    authors: str = ""           # 作者
    year: str = ""              # 发表年份
    source: str = ""            # 来源期刊/会议
    citations: int = 0          # 被引量
    abstract: str = ""          # 摘要
    url: str = ""               # 论文链接
    database: str = ""          # 来源数据库 (cnki/wos)
    language: str = "zh"        # 语言
    doi: str = ""               # DOI
    keywords: str = ""          # 关键词
    search_query: str = ""      # 使用的检索式
    is_from_citation: bool = False  # 是否来自引用扩展


@dataclass
class SearchResults:
    """检索结果集"""
    topic: str                  # 搜索主题
    search_query_cnki: str = "" # 知网检索式
    search_query_wos: str = ""  # WoS检索式
    total_cnki: int = 0         # 知网搜索结果总数
    total_wos: int = 0          # WoS搜索结果总数
    papers: list[PaperResult] = field(default_factory=list)  # 论文列表
    is_secondary: bool = False  # 是否为二次检索
    primary_topic: str = ""     # 一次检索的主题
