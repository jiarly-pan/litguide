"""英文标题翻译模块 — 将英文论文标题翻译为中文。"""

import re

# 学术常用词汇翻译表
_ACADEMIC_TERMS = {
    # 研究方法
    "review": "综述",
    "survey": "综述",
    "systematic review": "系统综述",
    "meta-analysis": "荟萃分析",
    "meta analysis": "荟萃分析",
    "machine learning": "机器学习",
    "deep learning": "深度学习",
    "neural network": "神经网络",
    "artificial intelligence": "人工智能",
    "natural language processing": "自然语言处理",
    "computer vision": "计算机视觉",
    "reinforcement learning": "强化学习",
    "transfer learning": "迁移学习",
    "federated learning": "联邦学习",
    "large language model": "大语言模型",
    "transformer": "Transformer模型",
    "attention mechanism": "注意力机制",
    "generative adversarial": "生成对抗",
    "convolutional neural": "卷积神经",
    "recurrent neural": "循环神经",
    "graph neural": "图神经",
    "random forest": "随机森林",
    "support vector": "支持向量",
    "logistic regression": "逻辑回归",
    "linear regression": "线性回归",
    "decision tree": "决策树",
    "gradient boosting": "梯度提升",
    "clustering": "聚类",
    "classification": "分类",
    "regression": "回归",
    "segmentation": "分割",
    "detection": "检测",
    "recognition": "识别",
    "prediction": "预测",
    "optimization": "优化",
    "simulation": "模拟",
    "modeling": "建模",
    "estimation": "估计",
    "evaluation": "评估",
    "comparison": "比较",
    "analysis": "分析",
    "synthesis": "合成",
    "framework": "框架",
    "approach": "方法",
    "method": "方法",
    "algorithm": "算法",
    "architecture": "架构",
    "system": "系统",
    "platform": "平台",
    "tool": "工具",
    "application": "应用",
    "implementation": "实现",
    "design": "设计",
    "development": "开发",
    "performance": "性能",
    "efficiency": "效率",
    "accuracy": "准确率",
    "robustness": "鲁棒性",
    "scalability": "可扩展性",

    # 研究领域
    "biomedical": "生物医学",
    "medical": "医学",
    "clinical": "临床",
    "healthcare": "医疗保健",
    "genomics": "基因组学",
    "proteomics": "蛋白质组学",
    "drug discovery": "药物发现",
    "diagnosis": "诊断",
    "prognosis": "预后",
    "treatment": "治疗",
    "therapy": "疗法",
    "cancer": "癌症",
    "tumor": "肿瘤",
    "disease": "疾病",
    "patient": "患者",
    "surgery": "手术",
    "imaging": "影像",
    "radiology": "放射学",
    "pathology": "病理学",

    # 计算机科学
    "software": "软件",
    "hardware": "硬件",
    "database": "数据库",
    "cloud computing": "云计算",
    "edge computing": "边缘计算",
    "internet of things": "物联网",
    "blockchain": "区块链",
    "cybersecurity": "网络安全",
    "privacy": "隐私",
    "security": "安全",
    "encryption": "加密",
    "authentication": "认证",
    "robotics": "机器人",
    "autonomous": "自主",
    "drone": "无人机",
    "vehicle": "车辆",
    "sensor": "传感器",
    "actuator": "执行器",

    # 材料/能源
    "material": "材料",
    "nanomaterial": "纳米材料",
    "graphene": "石墨烯",
    "polymer": "聚合物",
    "composite": "复合材料",
    "semiconductor": "半导体",
    "battery": "电池",
    "solar cell": "太阳能电池",
    "fuel cell": "燃料电池",
    "catalysis": "催化",
    "photocatalysis": "光催化",
    "electrocatalysis": "电催化",
    "energy storage": "储能",
    "renewable energy": "可再生能源",
    "hydrogen": "氢能",
    "carbon capture": "碳捕集",
    "sustainability": "可持续性",

    # 环境/生态
    "climate change": "气候变化",
    "global warming": "全球变暖",
    "pollution": "污染",
    "emission": "排放",
    "biodiversity": "生物多样性",
    "ecosystem": "生态系统",
    "conservation": "保护",
    "restoration": "恢复",
    "water quality": "水质",
    "air quality": "空气质量",
    "soil": "土壤",
    "wastewater": "废水",
    "recycling": "回收",

    # 社会科学
    "education": "教育",
    "economics": "经济学",
    "psychology": "心理学",
    "sociology": "社会学",
    "management": "管理",
    "marketing": "营销",
    "finance": "金融",
    "policy": "政策",
    "governance": "治理",
    "innovation": "创新",
    "entrepreneurship": "创业",
    "supply chain": "供应链",
    "logistics": "物流",

    # 常用连接词
    "based on": "基于",
    "based": "基于",
    "using": "使用",
    "via": "通过",
    "towards": "面向",
    "toward": "面向",
    "through": "通过",
    "between": "之间",
    "among": "之中",
    "within": "之内",
    "across": "跨",
    "beyond": "超越",
    "novel": "新型",
    "new": "新",
    "improved": "改进的",
    "enhanced": "增强的",
    "efficient": "高效的",
    "robust": "鲁棒的",
    "adaptive": "自适应的",
    "intelligent": "智能的",
    "smart": "智能的",
    "automated": "自动化的",
    "real-time": "实时",
    "online": "在线",
    "offline": "离线",
    "distributed": "分布式",
    "collaborative": "协作的",
    "interactive": "交互式",
    "multi-scale": "多尺度",
    "multi-modal": "多模态",
    "multi-task": "多任务",
    "end-to-end": "端到端",
    "state-of-the-art": "最先进",
    "comprehensive": "全面的",
    "comparative": "比较的",
    "systematic": "系统的",
    "empirical": "实证的",
    "theoretical": "理论的",
    "experimental": "实验的",
    "computational": "计算的",
    "data-driven": "数据驱动的",
    "knowledge-driven": "知识驱动的",
}


def translate_title(title: str) -> str:
    """将英文论文标题翻译为中文，使用术语匹配和规则翻译。"""
    if not title:
        return ""

    title_lower = title.lower().strip().rstrip(".")

    # 尝试逐词翻译
    translated_parts = []

    # 先匹配长词组
    remaining = title_lower
    while remaining:
        matched = False
        # 从长到短匹配
        for phrase, trans in sorted(_ACADEMIC_TERMS.items(), key=lambda x: -len(x[0])):
            if remaining.startswith(phrase):
                translated_parts.append(trans)
                remaining = remaining[len(phrase):]
                matched = True
                break

        if not matched:
            # 跳过一个字符
            if remaining[0].isalpha():
                translated_parts.append(remaining[0])
            remaining = remaining[1:]

    # 清理翻译结果
    if not translated_parts:
        return title  # 无法翻译时返回原标题

    # 将首字母增大写
    result = "".join(translated_parts)
    # 去除无意义的单个字母
    result = re.sub(r'\b[a-zA-Z]\b', '', result)
    # 清理多余空格
    result = re.sub(r'\s+', '', result)

    if len(result) < 3:
        return title

    return result


def translate_title_simple(title: str) -> str:
    """简单翻译：基于关键词替换。"""
    if not title:
        return ""

    title_lower = title.lower().rstrip(".")

    result = title_lower
    # 按长度排序，优先替换长词组
    for phrase, trans in sorted(_ACADEMIC_TERMS.items(), key=lambda x: -len(x[0])):
        if phrase in result:
            result = result.replace(phrase, trans)

    # 如果结果主要是英文，说明翻译不充分，保留原标题
    eng_chars = sum(1 for c in result if c.isascii() and c.isalpha())
    if eng_chars > len(result) * 0.6:
        return f"[待翻译] {title}"

    return result
