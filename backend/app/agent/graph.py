"""
LangGraph 状态图 — 多 Agent 工作流编排

架构：
  用户输入 → Supervisor（路由）→ Detection/Analysis/QA Agent → Summarize → END

使用方式：
  from app.agent.graph import build_multi_agent_graph
  graph = build_multi_agent_graph()
  async for event in graph.astream_events({"messages": [HumanMessage(...)]}, version="v2"):
      ...
"""

from langgraph.graph import END, StateGraph

from app.agent.detection_agent import create_llm
from app.agent.state import AgentState
from app.agent.sub_agents import make_analysis_node, make_detection_node, make_qa_node
from app.agent.supervisor import SupervisorAgent
from app.core.logger import get_logger

logger = get_logger(__name__)

# 模块级缓存：图只构建一次
_graph_cache = None


def build_multi_agent_graph():
    """
    构建并编译多 Agent 协作状态图（带缓存）

    Returns:
        编译后的 LangGraph CompiledGraph
    """
    global _graph_cache
    if _graph_cache is not None:
        return _graph_cache

    llm = create_llm()
    supervisor = SupervisorAgent(llm)

    # 构建各子 Agent 节点（闭包持有各自的 executor）
    detection_node = make_detection_node(llm)
    analysis_node = make_analysis_node(llm)
    qa_node = make_qa_node(llm)

    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("supervisor", supervisor.route)
    workflow.add_node("detection", detection_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("qa", qa_node)
    workflow.add_node("summarize", supervisor.summarize)

    # 入口：Supervisor 路由
    workflow.set_entry_point("supervisor")

    # 条件路由：根据 Supervisor 决策跳转
    workflow.add_conditional_edges(
        "supervisor",
        supervisor.decide_next,
        {
            "detection": "detection",
            "analysis": "analysis",
            "qa": "qa",
        },
    )

    # 各 Agent 执行完毕后进入汇总（直接透传，不二次调用 LLM）
    workflow.add_edge("detection", "summarize")
    workflow.add_edge("analysis", "summarize")
    workflow.add_edge("qa", "summarize")
    workflow.add_edge("summarize", END)

    compiled = workflow.compile()
    logger.info("LangGraph 多 Agent 状态图构建完成（detection / analysis / qa）")
    _graph_cache = compiled
    return compiled
"""
LangGraph 状态图 — 多 Agent 工作流编排

架构：
  用户输入 → Supervisor（路由）→ Detection/Analysis/QA Agent → 汇总 → 回复
"""

from langgraph.graph import END, StateGraph

from app.agent.state import AgentState
from app.core.logger import get_logger

logger = get_logger(__name__)


def build_agent_graph(llm, detection_agent_node, analysis_agent_node, qa_agent_node):
    """
    构建多 Agent 协作状态图

    Args:
        llm: LLM 实例
        detection_agent_node: 检测 Agent 节点函数
        analysis_agent_node: 分析 Agent 节点函数
        qa_agent_node: 问答 Agent 节点函数

    Returns:
        编译后的 LangGraph 图
    """
    from app.agent.supervisor import SupervisorAgent

    supervisor = SupervisorAgent(llm)

    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("supervisor", supervisor.route)
    workflow.add_node("detection", detection_agent_node)
    workflow.add_node("analysis", analysis_agent_node)
    workflow.add_node("qa", qa_agent_node)
    workflow.add_node("summarize", supervisor.summarize)

    # 设置入口
    workflow.set_entry_point("supervisor")

    # Supervisor 条件路由
    workflow.add_conditional_edges(
        "supervisor",
        supervisor.decide_next,
        {
            "detection": "detection",
            "analysis": "analysis",
            "qa": "qa",
        },
    )

    # 各 Agent 执行后进入汇总
    workflow.add_edge("detection", "summarize")
    workflow.add_edge("analysis", "summarize")
    workflow.add_edge("qa", "summarize")
    workflow.add_edge("summarize", END)

    compiled = workflow.compile()
    logger.info("LangGraph 多 Agent 状态图构建完成")
    return compiled