"""命令行入口 — 文献检索指导系统 CLI。"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from .models import PaperType, SearchGuidance
from .keywords import suggest_keywords
from .search_formula import build_all_formulas
from .filter_guide import generate_filter_advice
from .session import get_session, reset_session

console = Console()


def _select_type(paper_type_str: str) -> PaperType:
    """将用户输入映射到文献类型。"""
    mapping = {
        "综述": PaperType.REVIEW,
        "综述型": PaperType.REVIEW,
        "review": PaperType.REVIEW,
        "应用": PaperType.APPLIED,
        "应用型": PaperType.APPLIED,
        "方法": PaperType.APPLIED,
        "applied": PaperType.APPLIED,
        "前沿": PaperType.FRONTIER,
        "前沿探索": PaperType.FRONTIER,
        "frontier": PaperType.FRONTIER,
        "对比": PaperType.COMPARATIVE,
        "对比分析": PaperType.COMPARATIVE,
        "comparative": PaperType.COMPARATIVE,
    }
    return mapping.get(paper_type_str.strip(), PaperType.REVIEW)


def _display_guidance(guidance: SearchGuidance):
    """用 rich 格式化输出检索指导。"""

    # 标题
    console.print()
    console.rule("[bold blue]文献检索指导[/bold blue]")
    console.print(f"[bold]研究方向：[/bold]{guidance.topic}")
    console.print(f"[bold]文献类型：[/bold]{guidance.paper_type.value}")
    console.print()

    # 板块1：推荐检索词
    console.rule("[bold green]1. 推荐检索词[/bold green]")

    zh_table = Table(title="中文检索词", show_header=True, header_style="bold")
    zh_table.add_column("优先级", style="dim", width=8)
    zh_table.add_column("检索词", width=24)
    zh_table.add_column("推荐理由", width=20)
    for k in guidance.keywords_zh:
        star = "★ 主关键词" if k.is_primary else "  次要"
        style = "bold yellow" if k.is_primary else ""
        zh_table.add_row(star, k.word, k.rationale, style=style)
    console.print(zh_table)
    console.print()

    en_table = Table(title="英文检索词", show_header=True, header_style="bold")
    en_table.add_column("优先级", style="dim", width=10)
    en_table.add_column("Keyword", width=24)
    en_table.add_column("Rationale", width=20)
    for k in guidance.keywords_en:
        star = "★ Primary" if k.is_primary else "  Secondary"
        style = "bold yellow" if k.is_primary else ""
        en_table.add_row(star, k.word, k.rationale, style=style)
    console.print(en_table)
    console.print()

    # 板块2：推荐检索式
    console.rule("[bold green]2. 推荐检索式[/bold green]")

    for f in guidance.formulas:
        console.print(Panel(
            f"[bold cyan]{f.formula}[/bold cyan]\n\n[dim]{f.note}[/dim]",
            title=f"[bold]{f.database.label}[/bold] ({f.database.language})",
            border_style="blue",
        ))

    # 板块3：筛选建议
    console.rule("[bold green]3. 筛选建议[/bold green]")

    fa = guidance.filter_advice
    console.print(f"[bold]权重分配：[/bold]")
    console.print(f"  相关性: [yellow]{fa.weights['relevance']}%[/yellow]  |  引用量: [yellow]{fa.weights['citations']}%[/yellow]  |  时效性: [yellow]{fa.weights['recency']}%[/yellow]")
    console.print()
    console.print(f"[bold]年份策略：[/bold]{fa.year_strategy}")
    console.print(f"[bold]来源推荐：[/bold]{fa.source_strategy}")
    console.print()
    console.print("[bold]操作建议：[/bold]")
    for i, tip in enumerate(fa.tips, 1):
        console.print(f"  {i}. {tip}")

    console.print()
    console.rule()


@click.group()
def main():
    """文献检索指导系统 — 提供检索策略与筛选指导，不涉及文献下载。"""


@main.command()
@click.argument("topic")
@click.option("--type", "-t", "paper_type_str", default="综述型",
              help="文献类型：综述型 / 应用型 / 前沿探索型 / 对比分析型")
def search(topic: str, paper_type_str: str):
    """根据研究主题和文献类型生成检索策略。

    TOPIC: 研究方向或研究主题（如：机器学习、文献计量、人工智能）
    """
    paper_type = _select_type(paper_type_str)
    session = get_session()

    # 检查是否是被排除的方向
    if session.is_excluded(topic):
        console.print(f"[yellow][!] 注意：'{topic}' 此前已被排除，如需重新探索请使用 `litguide reset`[/yellow]")

    console.print(f"[dim]正在为「{topic}」生成 {paper_type.value} 检索策略...[/dim]")

    # 生成检索词
    zh_keywords, en_keywords = suggest_keywords(topic, paper_type)

    # 生成检索式
    formulas = build_all_formulas(zh_keywords, en_keywords)

    # 生成筛选建议
    filter_advice = generate_filter_advice(paper_type)

    # 记录到会话
    all_keywords = [k.word for k in zh_keywords + en_keywords]
    session.record_search(topic, paper_type.value, all_keywords)

    # 输出
    guidance = SearchGuidance(
        topic=topic,
        paper_type=paper_type,
        keywords_zh=zh_keywords,
        keywords_en=en_keywords,
        formulas=formulas,
        filter_advice=filter_advice,
    )
    _display_guidance(guidance)


@main.command()
def history():
    """查看本次会话的检索历史。"""
    session = get_session()
    console.print(Panel(session.summary(), title="[bold]检索历史[/bold]"))


@main.command()
@click.argument("topic")
def exclude(topic: str):
    """排除某研究方向，后续不再重复推荐。"""
    session = get_session()
    session.exclude_topic(topic)
    used = session.get_used_topics()
    console.print(f"[green][OK] 已排除「{topic}」，当前已检索/排除方向：{', '.join(used)}[/green]")


@main.command()
@click.argument("feedback")
def feedback(feedback: str):
    """记录用户反馈，用于后续优化建议。"""
    session = get_session()
    session.set_feedback(feedback)
    console.print(f"[green][OK] 已记录反馈：{feedback}[/green]")


@main.command()
def reset():
    """重置当前会话，清除所有历史和状态。"""
    reset_session()
    console.print("[green][OK] 会话已重置[/green]")


@main.command()
def types():
    """列出支持的文献类型及权重说明。"""
    table = Table(title="支持的文献类型", show_header=True, header_style="bold")
    table.add_column("类型", width=16)
    table.add_column("相关性权重", width=12)
    table.add_column("引用量权重", width=12)
    table.add_column("时效性权重", width=12)
    table.add_column("年份策略", width=16)

    for pt in PaperType:
        from .models import WEIGHT_TABLE, YEAR_STRATEGY
        w = WEIGHT_TABLE[pt]
        table.add_row(
            pt.value,
            f"{w['relevance']}%",
            f"{w['citations']}%",
            f"{w['recency']}%",
            YEAR_STRATEGY[pt],
        )

    console.print(table)


if __name__ == "__main__":
    main()
