"""
LangGraph 多 Agent 共享状态定义

AgentState 是所有 Agent 共享的状态容器，在 LangGraph 状态图中流转。
每个 Agent 读取和修改状态中的特定字段。
"""

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """多 Agent 共享状态"""

    # 对话消息列表（使用 add_messages reducer 自动追加）
    messages: Annotated[list, add_messages]

    # 路由决策
    next_agent: str  # "detection" | "analysis" | "qa"

    # 各 Agent 的执行结果
    detection_result: dict
    analysis_result: dict
    qa_result: str

    # 最终回复
    final_response: str

    # 用户信息
    user_id: int
    session_id: str