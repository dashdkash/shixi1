"""
Supervisor Agent — 意图识别与任务路由（混合执行模式）

职责：
  - 分析用户输入，识别意图（支持复合意图）
  - 决定执行方式：parallel（并行）或 chain（串行链）
  - 路由到 1~3 个子 Agent 执行
  - 汇总各 Agent 结果，生成最终回复

混合执行机制：
  - parallel: decide_next() 返回列表，触发 LangGraph fan-out 并行
  - chain: decide_next() 返回第一个 Agent，后续通过条件边依次串联
  - 所有 Agent 完成后，summarize() 统一汇总
"""

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.prompts import SUPERVISOR_ROUTING_PROMPT
from app.core.logger import get_logger

logger = get_logger(__name__)

# 合法的 Agent 名称集合
VALID_AGENTS = {"detection", "analysis", "qa"}


class SupervisorAgent:
    """主管 Agent（混合执行模式）"""

    def __init__(self, llm):
        self.llm = llm

    def route(self, state: dict) -> dict:
        """路由：识别用户意图，决定执行方式和 Agent 列表"""
        messages = [
            SystemMessage(content=SUPERVISOR_ROUTING_PROMPT),
            state["messages"][-1],  # 最新用户消息
        ]
        response = self.llm.invoke(messages)
        raw = response.content.strip().lower()

        # 解析格式："执行方式: agent1,agent2"
        execution_plan = "parallel"
        agents = []

        if ":" in raw:
            parts = raw.split(":", 1)
            plan_part = parts[0].strip()
            agents_part = parts[1].strip()

            # 解析执行方式
            if "chain" in plan_part:
                execution_plan = "chain"
            else:
                execution_plan = "parallel"

            # 解析 Agent 列表
            for name in agents_part.split(","):
                name = name.strip()
                if name in VALID_AGENTS and name not in agents:
                    agents.append(name)
        else:
            # 兼容旧格式（纯 Agent 名称列表）
            for name in raw.split(","):
                name = name.strip()
                if name in VALID_AGENTS and name not in agents:
                    agents.append(name)

        # 兆底：解析失败默认 qa
        if not agents:
            agents = ["qa"]
            execution_plan = "parallel"

        logger.info("Supervisor 路由决策: %s | 执行方式: %s (原始: %s)", agents, execution_plan, raw)
        return {"next_agents": agents, "execution_plan": execution_plan}

    def decide_next(self, state: dict) -> list[str] | str:
        """
        条件路由：
        - parallel 模式：返回 Agent 列表，LangGraph 自动 fan-out 并行执行
        - chain 模式：返回第一个 Agent（字符串），后续由 after_agent 条件边串联
        """
        agents = state.get("next_agents", ["qa"])
        plan = state.get("execution_plan", "parallel")

        if plan == "chain" and len(agents) > 1:
            # 串行链：只进入第一个节点
            logger.info("Chain 模式启动，第一个 Agent: %s，完整链: %s", agents[0], agents)
            return agents[0]
        else:
            # 并行：返回所有节点（fan-out）
            logger.info("Parallel 模式 fan-out: %s", agents)
            return agents

    def after_agent(self, current_agent: str):
        """
        生成条件边函数：判断当前 Agent 完成后下一步去哪。
        - chain 模式：如果当前 Agent 不是链中最后一个，进入下一个 Agent
        - parallel 模式或链末尾：进入 summarize
        """
        def _decide(state: dict) -> str:
            plan = state.get("execution_plan", "parallel")
            agents = state.get("next_agents", [])

            if plan == "chain" and current_agent in agents:
                idx = agents.index(current_agent)
                if idx + 1 < len(agents):
                    next_agent = agents[idx + 1]
                    logger.info("Chain: %s → %s", current_agent, next_agent)
                    return next_agent

            return "summarize"

        return _decide

    def summarize(self, state: dict) -> dict:
        """汇总：整合各 Agent 结果，生成最终回复"""
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
        if agent_count == 1:
            raw_result = context_parts[0]
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