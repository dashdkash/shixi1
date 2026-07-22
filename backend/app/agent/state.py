"""LangGraph 多 Agent 共享状态定义

AgentState 是所有 Agent 共享的状态容器，在 LangGraph 状态图中流转。
每个 Agent 读取和修改状态中的特定字段。

并行模式：
  - next_agents: Supervisor 选中的 Agent 列表（支持并行 fan-out）
  - 各子 Agent 将结果写入对应字段，summarize 节点统一汇总
"""

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """多 Agent 共享状态（并行模式）"""

    # 对话消息列表（使用 add_messages reducer 自动追加）
    messages: Annotated[list, add_messages]

    # ── 路由决策（并行模式） ──
    next_agents: list[str]  # Supervisor 选中的 Agent 列表，如 ["detection", "analysis"]

    # ── 各 Agent 的执行结果 ──
    detection_result: dict
    analysis_result: dict
    qa_result: str

    # ── 最终回复（由 summarize 节点生成） ──
    final_response: str

    # ── 用户信息 ──
    user_id: int
    session_id: str