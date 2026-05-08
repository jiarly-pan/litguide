"""文献检索指导系统 GUI — 基于 Tkinter 的窗口界面。"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue

from .models import PaperType
from .keywords import suggest_keywords
from .search_formula import build_all_formulas
from .filter_guide import generate_filter_advice
from .session import get_session, reset_session


def _run_search(topic, paper_type, result_queue):
    """在后台线程中执行检索策略生成。"""
    try:
        pt = _parse_type(paper_type)
        zh_kw, en_kw = suggest_keywords(topic, pt)
        formulas = build_all_formulas(zh_kw, en_kw)
        advice = generate_filter_advice(pt)

        session = get_session()
        all_kw = [k.word for k in zh_kw + en_kw]
        session.record_search(topic, pt.value, all_kw)

        result_queue.put(("ok", (topic, pt, zh_kw, en_kw, formulas, advice)))
    except Exception as e:
        result_queue.put(("error", str(e)))


def _parse_type(type_str):
    mapping = {
        "综述型": PaperType.REVIEW, "应用/方法型": PaperType.APPLIED,
        "前沿探索型": PaperType.FRONTIER, "对比分析型": PaperType.COMPARATIVE,
        "review": PaperType.REVIEW, "applied": PaperType.APPLIED,
        "frontier": PaperType.FRONTIER, "comparative": PaperType.COMPARATIVE,
    }
    return mapping.get(type_str, PaperType.REVIEW)


class LitGuideApp:
    """文献检索指导系统主窗口。"""

    def __init__(self, root):
        self.root = root
        self.root.title("文献检索指导系统 v1.0")
        self.root.geometry("860x680")
        self.root.resizable(True, True)

        # 设置样式
        style = ttk.Style()
        style.theme_use("clam")

        self._build_input_frame()
        self._build_output_frame()
        self._build_status_bar()

    def _build_input_frame(self):
        """顶部输入区域。"""
        frame = ttk.LabelFrame(self.root, text="输入检索条件", padding=10)
        frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        # 第1行：主题输入
        ttk.Label(frame, text="研究主题：", font=("", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.topic_var = tk.StringVar()
        topic_entry = ttk.Entry(frame, textvariable=self.topic_var, width=40, font=("", 11))
        topic_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        topic_entry.focus_set()

        # 第2行：文献类型
        ttk.Label(frame, text="文献类型：", font=("", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.type_var = tk.StringVar(value="综述型")
        type_combo = ttk.Combobox(frame, textvariable=self.type_var, width=20,
                                  values=["综述型", "应用/方法型", "前沿探索型", "对比分析型"],
                                  state="readonly", font=("", 10))
        type_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # 第3行：按钮区
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))

        self.search_btn = ttk.Button(btn_frame, text="🔍 生成检索策略", command=self._on_search)
        self.search_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.history_btn = ttk.Button(btn_frame, text="📋 检索历史", command=self._show_history)
        self.history_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.types_btn = ttk.Button(btn_frame, text="📊 权重说明", command=self._show_types)
        self.types_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.reset_btn = ttk.Button(btn_frame, text="🔄 重置会话", command=self._reset)
        self.reset_btn.pack(side=tk.LEFT)

        # 绑定回车键
        topic_entry.bind("<Return>", lambda e: self._on_search())

    def _build_output_frame(self):
        """下部输出区域。"""
        frame = ttk.LabelFrame(self.root, text="检索指导结果", padding=5)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 文本输出区（带滚动条）
        self.output_text = tk.Text(frame, wrap=tk.WORD, font=("Consolas", 10),
                                   padx=10, pady=10, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(frame, command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=scrollbar.set)

        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 配置文本标签样式
        self.output_text.tag_configure("title", font=("", 12, "bold"), foreground="#1a5276")
        self.output_text.tag_configure("section", font=("", 11, "bold"), foreground="#2e86c1")
        self.output_text.tag_configure("primary", font=("", 10, "bold"), foreground="#d35400")
        self.output_text.tag_configure("highlight", font=("", 10, "bold"), foreground="#27ae60")
        self.output_text.tag_configure("formula", font=("Consolas", 11, "bold"), foreground="#8e44ad")
        self.output_text.tag_configure("note", font=("", 9), foreground="#7f8c8d")
        self.output_text.tag_configure("tip", font=("", 10), foreground="#2c3e50")

    def _build_status_bar(self):
        """底部状态栏。"""
        self.status_var = tk.StringVar(value="就绪 — 输入研究主题，点击「生成检索策略」开始")
        status_bar = ttk.Label(self.root, textvariable=self.status_var,
                               relief=tk.SUNKEN, anchor=tk.W, padding=5)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _append_text(self, text, tag=None):
        """安全地向输出区追加文本。"""
        self.output_text.configure(state=tk.NORMAL)
        if tag:
            self.output_text.insert(tk.END, text, tag)
        else:
            self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.configure(state=tk.DISABLED)
        self.root.update_idletasks()

    def _clear_output(self):
        """清空输出区。"""
        self.output_text.configure(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.configure(state=tk.DISABLED)

    def _on_search(self):
        """点击搜索按钮。"""
        topic = self.topic_var.get().strip()
        if not topic:
            messagebox.showwarning("提示", "请输入研究主题。")
            return

        self._clear_output()
        self.search_btn.configure(state=tk.DISABLED)
        self.status_var.set(f"正在为「{topic}」生成检索策略...")

        # 后台线程执行
        result_queue = queue.Queue()
        thread = threading.Thread(target=_run_search,
                                  args=(topic, self.type_var.get(), result_queue),
                                  daemon=True)
        thread.start()
        self.root.after(100, self._check_result, result_queue)

    def _check_result(self, result_queue):
        """轮询后台任务结果。"""
        try:
            status, data = result_queue.get_nowait()
            self.search_btn.configure(state=tk.NORMAL)

            if status == "error":
                self.status_var.set("生成失败")
                messagebox.showerror("错误", f"检索策略生成失败：{data}")
                return

            self._display_guidance(data)
            self.status_var.set(f"完成 — 已为「{data[0]}」生成 {data[1].value} 检索策略")

        except queue.Empty:
            self.root.after(100, self._check_result, result_queue)

    def _display_guidance(self, data):
        """格式化显示检索指导。"""
        topic, pt, zh_kw, en_kw, formulas, advice = data

        self._append_text("\n")
        self._append_text("═" * 70 + "\n", "title")
        self._append_text(f"  研究方向：{topic}\n", "title")
        self._append_text(f"  文献类型：{pt.value}\n", "title")
        self._append_text("═" * 70 + "\n\n", "title")

        # 板块1：检索词
        self._append_text("━" * 70 + "\n", "section")
        self._append_text("  1. 推荐检索词\n", "section")
        self._append_text("━" * 70 + "\n\n", "section")

        self._append_text("  【中文检索词】\n", "highlight")
        for k in zh_kw:
            star = "★" if k.is_primary else " ·"
            tag = "primary" if k.is_primary else None
            self._append_text(f"    {star} {k.word:<24s} — {k.rationale}\n", tag)

        self._append_text("\n  【英文检索词】\n", "highlight")
        for k in en_kw:
            star = "★" if k.is_primary else " ·"
            tag = "primary" if k.is_primary else None
            self._append_text(f"    {star} {k.word:<30s} — {k.rationale}\n", tag)

        self._append_text("\n")

        # 板块2：检索式
        self._append_text("━" * 70 + "\n", "section")
        self._append_text("  2. 推荐检索式\n", "section")
        self._append_text("━" * 70 + "\n\n", "section")

        for f in formulas:
            self._append_text(f"  【{f.database.label}】({f.database.language})\n", "highlight")
            self._append_text(f"    {f.formula}\n", "formula")
            self._append_text(f"    {f.note}\n\n", "note")

        # 板块3：筛选建议
        self._append_text("━" * 70 + "\n", "section")
        self._append_text("  3. 筛选建议\n", "section")
        self._append_text("━" * 70 + "\n\n", "section")

        w = advice.weights
        self._append_text(f"  权重分配：相关性 {w['relevance']}%  |  引用量 {w['citations']}%  |  时效性 {w['recency']}%\n")
        self._append_text(f"  年份策略：{advice.year_strategy}\n")
        self._append_text(f"  来源推荐：{advice.source_strategy}\n\n")
        self._append_text("  操作建议：\n", "highlight")
        for i, tip in enumerate(advice.tips, 1):
            self._append_text(f"    {i}. {tip}\n", "tip")

        self._append_text("\n")
        self._append_text("═" * 70 + "\n", "title")

    def _show_history(self):
        """显示检索历史。"""
        session = get_session()
        history = session.summary()
        self._clear_output()
        self._append_text("\n")
        self._append_text("━" * 70 + "\n", "section")
        self._append_text("  检索历史\n", "section")
        self._append_text("━" * 70 + "\n\n", "section")
        self._append_text(f"  {history}\n")
        self.status_var.set("已显示检索历史")

    def _show_types(self):
        """显示文献类型权重表。"""
        from .models import WEIGHT_TABLE, YEAR_STRATEGY, SOURCE_STRATEGY
        self._clear_output()
        self._append_text("\n")
        self._append_text("━" * 70 + "\n", "section")
        self._append_text("  文献类型与权重说明\n", "section")
        self._append_text("━" * 70 + "\n\n", "section")

        for pt in PaperType:
            w = WEIGHT_TABLE[pt]
            self._append_text(f"  【{pt.value}】\n", "highlight")
            self._append_text(f"    权重：相关性 {w['relevance']}% | 引用量 {w['citations']}% | 时效性 {w['recency']}%\n")
            self._append_text(f"    年份：{YEAR_STRATEGY[pt]}\n")
            self._append_text(f"    来源：{SOURCE_STRATEGY[pt]}\n\n")

        self.status_var.set("已显示权重说明")

    def _reset(self):
        """重置会话。"""
        if messagebox.askyesno("确认", "确定要清除所有检索历史和状态吗？"):
            reset_session()
            self._clear_output()
            self.status_var.set("会话已重置")
            messagebox.showinfo("提示", "会话已重置。")


def main():
    """启动 GUI。"""
    root = tk.Tk()
    app = LitGuideApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
