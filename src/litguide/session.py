"""会话状态追踪 — 记录多轮对话中的检索历史与用户反馈。"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class SessionRecord:
    """单次检索的记录。"""
    topic: str
    paper_type: str
    keywords_used: list[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SessionState:
    """会话状态，追踪多轮对话。"""
    history: list[SessionRecord] = field(default_factory=list)
    excluded_topics: set[str] = field(default_factory=set)
    last_feedback: str = ""

    def record_search(self, topic: str, paper_type: str, keywords: list[str]):
        """记录一次检索。"""
        self.history.append(SessionRecord(
            topic=topic,
            paper_type=paper_type,
            keywords_used=keywords,
        ))

    def get_used_keywords(self) -> set[str]:
        """获取所有已使用过的检索词。"""
        used = set()
        for record in self.history:
            used.update(k.lower() for k in record.keywords_used)
        return used

    def get_used_topics(self) -> set[str]:
        """获取所有已检索过的主题。"""
        return {r.topic.lower() for r in self.history}

    def exclude_topic(self, topic: str):
        """排除某研究方向。"""
        self.excluded_topics.add(topic.lower())

    def set_feedback(self, feedback: str):
        """记录用户反馈。"""
        self.last_feedback = feedback

    def is_excluded(self, topic: str) -> bool:
        """检查主题是否已被排除。"""
        return topic.lower() in self.excluded_topics

    def summary(self) -> str:
        """会话摘要。"""
        if not self.history:
            return "（新会话，无历史记录）"
        lines = [f"已进行 {len(self.history)} 次检索："]
        for i, r in enumerate(self.history[-5:], 1):
            lines.append(f"  {i}. [{r.paper_type}] {r.topic} → 关键词: {', '.join(r.keywords_used[:3])}...")
        if self.excluded_topics:
            lines.append(f"已排除方向: {', '.join(self.excluded_topics)}")
        return "\n".join(lines)

    def save(self, path: Path):
        """持久化会话状态。"""
        data = {
            "history": [
                {"topic": r.topic, "paper_type": r.paper_type, "keywords_used": r.keywords_used, "timestamp": r.timestamp}
                for r in self.history
            ],
            "excluded_topics": list(self.excluded_topics),
            "last_feedback": self.last_feedback,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "SessionState":
        """从文件恢复会话状态。"""
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            state = cls()
            state.history = [
                SessionRecord(**r) for r in data.get("history", [])
            ]
            state.excluded_topics = set(data.get("excluded_topics", []))
            state.last_feedback = data.get("last_feedback", "")
            return state
        except (json.JSONDecodeError, KeyError):
            return cls()


# 全局会话实例（进程内持久化 + 文件持久化）
_session: SessionState | None = None
_SESSION_FILE = Path.home() / ".litguide_session.json"


def get_session() -> SessionState:
    """获取当前会话状态，自动从文件恢复。"""
    global _session
    if _session is None:
        _session = SessionState.load(_SESSION_FILE)
    return _session


def reset_session():
    """重置全局会话状态。"""
    global _session
    _session = SessionState()
    # 删除持久化文件
    if _SESSION_FILE.exists():
        _SESSION_FILE.unlink()


def _save_session():
    """在进程退出前保存会话到文件。"""
    if _session is not None and _session.history:
        _session.save(_SESSION_FILE)


# 注册退出时自动保存
import atexit
atexit.register(_save_session)
