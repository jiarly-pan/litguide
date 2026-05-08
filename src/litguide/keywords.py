"""检索词推荐引擎 — 根据研究方向生成中英文检索词。"""

from .models import KeywordEntry, PaperType


# 领域词根映射表（中文 → 英文候选词组）
_DOMAIN_LEXICON = {
    "机器学习": {
        "zh": [("机器学习", True), ("深度学习", False), ("神经网络", False), ("模型训练", False), ("监督学习", False), ("无监督学习", False), ("强化学习", False), ("迁移学习", False)],
        "en": [("machine learning", True), ("deep learning", False), ("neural network", False), ("model training", False), ("supervised learning", False), ("unsupervised learning", False), ("reinforcement learning", False), ("transfer learning", False)],
    },
    "人工智能": {
        "zh": [("人工智能", True), ("大语言模型", False), ("自然语言处理", False), ("计算机视觉", False), ("知识图谱", False), ("多模态", False)],
        "en": [("artificial intelligence", True), ("large language model", False), ("natural language processing", False), ("computer vision", False), ("knowledge graph", False), ("multimodal", False)],
    },
    "深度学习": {
        "zh": [("深度学习", True), ("卷积神经网络", False), ("循环神经网络", False), ("Transformer", False), ("注意力机制", False), ("预训练模型", False), ("生成对抗网络", False)],
        "en": [("deep learning", True), ("convolutional neural network", False), ("recurrent neural network", False), ("Transformer", False), ("attention mechanism", False), ("pre-trained model", False), ("GAN", False)],
    },
    "文献计量": {
        "zh": [("文献计量", True), ("引文分析", False), ("科学知识图谱", False), ("共词分析", False), ("研究热点", False), ("CiteSpace", False)],
        "en": [("bibliometrics", True), ("citation analysis", False), ("scientometric", False), ("co-word analysis", False), ("research trends", False), ("VOSviewer", False)],
    },
}

# 文献类型对应的修饰词
_TYPE_MODIFIERS = {
    PaperType.REVIEW: {
        "zh": [("综述", True), ("研究进展", False), ("研究现状", False), ("回顾", False), ("展望", False)],
        "en": [("review", True), ("survey", False), ("state of the art", False), ("systematic review", False), ("meta-analysis", False)],
    },
    PaperType.APPLIED: {
        "zh": [("方法", True), ("应用", False), ("实现", False), ("案例分析", False), ("实证研究", False)],
        "en": [("method", True), ("application", False), ("implementation", False), ("case study", False), ("empirical study", False)],
    },
    PaperType.FRONTIER: {
        "zh": [("前沿", True), ("最新", False), ("新兴", False), ("突破", False), ("预印本", False)],
        "en": [("novel", True), ("state-of-the-art", False), ("emerging", False), ("breakthrough", False), ("preprint", False)],
    },
    PaperType.COMPARATIVE: {
        "zh": [("对比", True), ("比较研究", False), ("差异分析", False), ("基准测试", False), ("评估", False)],
        "en": [("comparative", True), ("comparison", False), ("benchmark", False), ("evaluation", False), ("cross-domain", False)],
    },
}


def _fuzzy_match(query: str) -> dict:
    """模糊匹配领域词根，返回匹配到的词条。"""
    query_lower = query.lower().strip()
    for key, value in _DOMAIN_LEXICON.items():
        if key.lower() in query_lower or query_lower in key.lower():
            return value
    return None


def _suggest_generic(query: str) -> dict:
    """对未命中词根表的查询，生成通用检索词。"""
    return {
        "zh": [(query, True)],
        "en": [(query, True)],
    }


def suggest_keywords(topic: str, paper_type: PaperType) -> tuple[list[KeywordEntry], list[KeywordEntry]]:
    """根据研究主题和文献类型生成中英文检索词推荐。

    返回 (中文关键词列表, 英文关键词列表)
    """
    domain = _fuzzy_match(topic)
    if domain is None:
        domain = _suggest_generic(topic)

    modifiers = _TYPE_MODIFIERS[paper_type]

    zh_keywords = []
    en_keywords = []

    # 领域核心词
    for word, is_primary in domain.get("zh", []):
        zh_keywords.append(KeywordEntry(word=word, language="zh", is_primary=is_primary, rationale="领域核心词" if is_primary else "领域扩展词"))

    # 文献类型修饰词
    for word, is_primary in modifiers.get("zh", []):
        zh_keywords.append(KeywordEntry(word=word, language="zh", is_primary=is_primary, rationale="类型限定词" if is_primary else "类型扩展词"))

    # 英文领域核心词
    for word, is_primary in domain.get("en", []):
        en_keywords.append(KeywordEntry(word=word, language="en", is_primary=is_primary, rationale="Core domain term" if is_primary else "Extended domain term"))

    # 英文类型修饰词
    for word, is_primary in modifiers.get("en", []):
        en_keywords.append(KeywordEntry(word=word, language="en", is_primary=is_primary, rationale="Type qualifier" if is_primary else "Type extension"))

    return zh_keywords, en_keywords
