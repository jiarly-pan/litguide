# 文献检索指导系统 (LitGuide)

辅助文献搜索的智能工具。输入研究主题，自动生成中英文检索词、数据库检索式和筛选策略。

**不涉及文献下载**，仅提供检索策略与筛选指导。

## 快速开始

```bash
pip install -e .
litguide search "机器学习" -t 综述型
```

## 启动方式

| 方式 | 命令 |
|------|------|
| 窗口界面 | `litguide-gui` 或双击 `run_litguide.bat` |
| 命令行 | `litguide search "主题" -t 类型` |

## 命令

| 命令 | 说明 |
|------|------|
| `litguide search TOPIC -t TYPE` | 生成检索策略 |
| `litguide types` | 查看文献类型与权重 |
| `litguide history` | 查看检索历史 |
| `litguide exclude TOPIC` | 排除某研究方向 |
| `litguide reset` | 重置会话 |

## 支持的文献类型

| 类型 | 权重(相关性/引用量/时效性) | 年份策略 |
|------|---------------------------|----------|
| 综述型 | 40% / 35% / 25% | 经典 + 近5年 |
| 应用/方法型 | 50% / 20% / 30% | 近3-5年 |
| 前沿探索型 | 30% / 15% / 55% | 近1-2年 |
| 对比分析型 | 45% / 30% / 25% | 宽年份跨度 |

## 支持的数据库

- CNKI（知网）
- Web of Science
- Semantic Scholar
- Crossref

## 项目结构

```
litguide/
├── pyproject.toml
├── run_litguide.bat           # 一键启动GUI
├── run_litguide_cli.bat       # 一键启动CLI
└── src/litguide/
    ├── cli.py                 # 命令行界面
    ├── gui.py                 # Tkinter 窗口界面
    ├── models.py              # 数据模型 + 权重配置
    ├── keywords.py            # 检索词推荐引擎
    ├── search_formula.py      # 检索式生成器
    ├── filter_guide.py        # 筛选指导生成器
    └── session.py             # 会话状态追踪
```
