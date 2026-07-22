"""LangGraph 多 Agent 共享状态定义

AgentState 是所有 Agent 共享的状态容器，在 LangGraph 状态图中流转。
每个 Agent 读取和修改状态中的特定字段。

混合执行模式：
  - execution_plan: "parallel"（并行）或 "chain"（串行链）
  - next_agents: Supervisor 选中的 Agent 列表
  - parallel 模式：所有 Agent 同时执行（fan-out），完成后汇总（fan-in）
  - chain 模式：按列表顺序依次执行，后者可读取前者结果
"""

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """多 Agent 共享状态（混合执行模式）"""

    # 对话消息列表（使用 add_messages reducer 自动追加）
    messages: Annotated[list, add_messages]

    # ── 路由决策 ──
    execution_plan: str  # "parallel"（并行）或 "chain"（串行链）
    next_agents: list[str]  # Supervisor 选中的 Agent 列表，如 ["detection", "qa"]

    # ── 各 Agent 的执行结果 ──
    detection_result: dict
    analysis_result: dict
    qa_result: str

    # ── 最终回复（由 summarize 节点生成） ──
    final_response: str

    # ── 用户信息 ──
    user_id: int
    session_id: str