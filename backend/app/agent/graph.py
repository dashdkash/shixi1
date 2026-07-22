"""
LangGraph 状态图 — 混合执行多 Agent 工作流编排

架构：
  用户输入 → Supervisor（路由）→ [Detection, Analysis, QA] → Summarize → END

混合执行机制：
  - parallel 模式：Supervisor 返回列表，LangGraph fan-out 并行执行，完成后 fan-in 汇总
  - chain 模式：Supervisor 返回第一个 Agent，各节点通过条件边依次串联，
    后者可读取前者结果（如：检测出草种 → QA 根据草种检索防治方案）

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
    构建并编译混合执行多 Agent 协作状态图（带缓存）

    支持两种执行拓扑：
    - parallel: 无依赖任务并行执行（fan-out/fan-in）
    - chain: 有依赖任务串行执行（后者可读取前者结果）

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

    # 条件路由：
    # - parallel 模式：decide_next 返回列表 → LangGraph 自动 fan-out
    # - chain 模式：decide_next 返回第一个 Agent 字符串
    workflow.add_conditional_edges(
        "supervisor",
        supervisor.decide_next,
        {
            "detection": "detection",
            "analysis": "analysis",
            "qa": "qa",
        },
    )

    # 各 Agent 完成后的条件边：
    # - chain 模式：如果当前 Agent 不是链末尾，进入下一个 Agent
    # - parallel 模式或链末尾：进入 summarize
    workflow.add_conditional_edges(
        "detection",
        supervisor.after_agent("detection"),
        {
            "analysis": "analysis",
            "qa": "qa",
            "summarize": "summarize",
        },
    )
    workflow.add_conditional_edges(
        "analysis",
        supervisor.after_agent("analysis"),
        {
            "qa": "qa",
            "summarize": "summarize",
        },
    )
    workflow.add_conditional_edges(
        "qa",
        supervisor.after_agent("qa"),
        {
            "summarize": "summarize",
        },
    )

    workflow.add_edge("summarize", END)

    compiled = workflow.compile()
    logger.info("LangGraph 混合执行多 Agent 状态图构建完成（支持 parallel + chain）")
    _graph_cache = compiled
    return compiled
