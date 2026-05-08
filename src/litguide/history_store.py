"""检索历史持久化存储 — 将检索记录保存到本地 JSON 文件。"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


HISTORY_FILE = Path.home() / ".litguide_search_history.json"
MAX_RECORDS = 100  # 最多保留 100 条记录


@dataclass
class HistoryRecord:
    """一条检索历史记录。"""
    id: str
    topic: str
    timestamp: str  # ISO 格式时间
    search_query_cnki: str
    search_query_wos: str
    total_count: int
    cnki_count: int
    wos_count: int
    citation_count: int
    is_secondary: bool = False
    primary_topic: str = ""
    top_titles: list = field(default_factory=list)  # 前 5 篇论文标题预览
    papers: list = field(default_factory=list)  # 完整论文列表


def _load_all() -> list[dict]:
    """从文件加载所有历史记录。"""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def _save_all(records: list[dict]) -> None:
    """保存所有历史记录到文件。"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    # 限制最多 MAX_RECORDS 条
    if len(records) > MAX_RECORDS:
        records = records[:MAX_RECORDS]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def save_search(topic: str, search_query_cnki: str, search_query_wos: str,
                total_count: int, cnki_count: int, wos_count: int,
                citation_count: int = 0, is_secondary: bool = False,
                primary_topic: str = "", papers: list = None) -> str:
    """保存一次检索记录，返回记录 ID。"""
    if papers is None:
        papers = []

    record_id = str(int(time.time() * 1000))
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    # 提取前 5 篇论文标题用于预览
    top_titles = []
    for p in papers[:5]:
        top_titles.append({
            "title": p.get("title", p.title if hasattr(p, "title") else ""),
            "language": p.get("language", p.language if hasattr(p, "language") else ""),
            "citations": p.get("citations", p.citations if hasattr(p, "citations") else 0),
        })

    record = HistoryRecord(
        id=record_id,
        topic=topic,
        timestamp=timestamp,
        search_query_cnki=search_query_cnki,
        search_query_wos=search_query_wos,
        total_count=total_count,
        cnki_count=cnki_count,
        wos_count=wos_count,
        citation_count=citation_count,
        is_secondary=is_secondary,
        primary_topic=primary_topic,
        top_titles=top_titles,
        papers=papers,
    )

    records = _load_all()
    records.insert(0, asdict(record))
    _save_all(records)

    return record_id


def list_records() -> list[dict]:
    """列出所有历史记录（不含完整论文数据，仅预览信息）。"""
    records = _load_all()
    summaries = []
    for r in records:
        summary = {
            "id": r.get("id"),
            "topic": r.get("topic"),
            "timestamp": r.get("timestamp"),
            "search_query_cnki": r.get("search_query_cnki"),
            "search_query_wos": r.get("search_query_wos"),
            "total_count": r.get("total_count"),
            "cnki_count": r.get("cnki_count"),
            "wos_count": r.get("wos_count"),
            "citation_count": r.get("citation_count", 0),
            "is_secondary": r.get("is_secondary", False),
            "primary_topic": r.get("primary_topic", ""),
            "top_titles": r.get("top_titles", []),
        }
        summaries.append(summary)
    return summaries


def get_record(record_id: str) -> Optional[dict]:
    """获取单条记录的完整数据（含论文列表）。"""
    records = _load_all()
    for r in records:
        if r.get("id") == record_id:
            return r
    return None


def delete_record(record_id: str) -> bool:
    """删除一条记录。"""
    records = _load_all()
    new_records = [r for r in records if r.get("id") != record_id]
    if len(new_records) < len(records):
        _save_all(new_records)
        return True
    return False


def clear_all() -> int:
    """清空所有历史记录，返回清除的条数。"""
    records = _load_all()
    count = len(records)
    _save_all([])
    return count


def search_history(query: str) -> list[dict]:
    """在历史记录中搜索（按主题模糊匹配）。"""
    records = list_records()
    query_lower = query.lower()
    return [r for r in records if query_lower in r.get("topic", "").lower()]
