"""
Supervisor Agent — 意图识别与任务路由（并行模式）

职责：
  - 分析用户输入，识别意图（支持复合意图）
  - 路由到 1~3 个子 Agent 并行执行（fan-out）
  - 汇总各 Agent 结果，生成最终回复（fan-in）

并行机制：
  - route() 返回 next_agents 列表，如 ["detection", "analysis"]
  - decide_next() 返回列表触发 LangGraph fan-out
  - 所有选中 Agent 完成后，summarize() 统一汇总
"""

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.prompts import SUPERVISOR_ROUTING_PROMPT
from app.core.logger import get_logger

logger = get_logger(__name__)

# 合法的 Agent 名称集合
VALID_AGENTS = {"detection", "analysis", "qa"}


class SupervisorAgent:
    """主管 Agent（并行模式）"""

    def __init__(self, llm):
        self.llm = llm

    def route(self, state: dict) -> dict:
        """路由：识别用户意图，决定交给哪些 Agent（支持多选）"""
        messages = [
            SystemMessage(content=SUPERVISOR_ROUTING_PROMPT),
            state["messages"][-1],  # 最新用户消息
        ]
        response = self.llm.invoke(messages)
        raw = response.content.strip().lower()

        # 解析逗号分隔的 Agent 名称列表
        agents = []
        for name in raw.split(","):
            name = name.strip()
            if name in VALID_AGENTS and name not in agents:
                agents.append(name)

        # 兜底：如果解析失败，默认 qa
        if not agents:
            agents = ["qa"]

        logger.info("Supervisor 路由决策: %s (原始: %s)", agents, raw)
        return {"next_agents": agents}

    def decide_next(self, state: dict) -> list[str]:
        """条件路由：返回 Agent 列表，LangGraph 自动 fan-out 并行执行"""
        agents = state.get("next_agents", ["qa"])
        logger.info("LangGraph fan-out: %s", agents)
        return agents

    def summarize(self, state: dict) -> dict:
        """汇总：整合各 Agent 结果，生成最终回复（fan-in 后执行）"""
        context_parts = []
        agent_count = 0

        if state.get("detection_result"):
            agent_count += 1
            result = state["detection_result"]
            if isinstance(result, dict) and result.get("output"):
                context_parts.append(f"检测结果：{result['output']}")
            else:
                context_parts.append(f"检测结果：{result}")

        if state.get("analysis_result"):
            agent_count += 1
            result = state["analysis_result"]
            if isinstance(result, dict) and result.get("output"):
                context_parts.append(f"分析结果：{result['output']}")
            else:
                context_parts.append(f"分析结果：{result}")

        if state.get("qa_result"):
            agent_count += 1
            context_parts.append(f"问答结果：{state['qa_result']}")

        if not context_parts:
            return {"final_response": "抱歉，我没有理解您的请求，请重新描述。"}

        # 始终调用 LLM 生成最终回复，确保流式输出 text_chunk 事件
        # 单 Agent 时用简化提示词减少延迟，多 Agent 时强调整合
        if agent_count == 1:
            raw_result = context_parts[0]
            # 去掉前缀
            for prefix in ["检测结果：", "分析结果：", "问答结果："]:
                if raw_result.startswith(prefix):
                    raw_result = raw_result[len(prefix):]
                    break
            summary_prompt = (
                f"请用简洁专业的中文向用户转述以下结果，不要添加额外内容：\n\n{raw_result}"
            )
        else:
            summary_prompt = (
                f"根据以下多个 Agent 的处理结果，生成一份统一简洁的中文回复：\n\n"
                + "\n\n".join(context_parts)
                + "\n\n要求：\n"
                "- 整合所有结果，不要遗漏\n"
                "- 回复简洁专业，避免重复\n"
                "- 如果检测结果中有标注图 URL，在回复中引导用户查看"
            )

        response = self.llm.invoke([HumanMessage(content=summary_prompt)])
        return {"final_response": response.content}