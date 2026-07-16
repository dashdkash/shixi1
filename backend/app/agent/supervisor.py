"""
Supervisor Agent — 意图识别与任务路由

职责：
  - 分析用户输入，识别意图
  - 路由到对应的子 Agent（detection / analysis / qa）
  - 汇总各 Agent 结果，生成最终回复
"""

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.prompts import SUPERVISOR_ROUTING_PROMPT
from app.core.logger import get_logger

logger = get_logger(__name__)


class SupervisorAgent:
    """主管 Agent"""

    def __init__(self, llm):
        self.llm = llm

    def route(self, state: dict) -> dict:
        """路由：识别用户意图，决定交给哪个 Agent"""
        messages = [
            SystemMessage(content=SUPERVISOR_ROUTING_PROMPT),
            state["messages"][-1],  # 最新用户消息
        ]
        response = self.llm.invoke(messages)
        next_agent = response.content.strip().lower()

        logger.info("Supervisor 路由决策: %s", next_agent)
        return {"next_agent": next_agent}

    def decide_next(self, state: dict) -> str:
        """条件路由：根据 Supervisor 决策跳转"""
        next_agent = state.get("next_agent", "qa")
        if "detection" in next_agent:
            return "detection"
        elif "analysis" in next_agent:
            return "analysis"
        else:
            return "qa"

    def summarize(self, state: dict) -> dict:
        """汇总：整合各 Agent 结果，生成最终回复"""
        context_parts = []
        if state.get("detection_result"):
            context_parts.append(f"检测结果：{state['detection_result']}")
        if state.get("analysis_result"):
            context_parts.append(f"分析结果：{state['analysis_result']}")
        if state.get("qa_result"):
            context_parts.append(f"问答结果：{state['qa_result']}")

        if not context_parts:
            return {"final_response": "抱歉，我没有理解您的请求，请重新描述。"}

        summary_prompt = (
            f"根据以下信息，生成一份简洁专业的中文回复：\n\n"
            + "\n".join(context_parts)
        )
        response = self.llm.invoke([HumanMessage(content=summary_prompt)])
        return {"final_response": response.content}