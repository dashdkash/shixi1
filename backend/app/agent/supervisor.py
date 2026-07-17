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
        if state.get("detection_result") and isinstance(state["detection_result"], dict):
            det_result = state["detection_result"]
            if "error" in det_result:
                return {"final_response": det_result["error"]}
            
            total_objects = det_result.get("total_objects", 0)
            class_counts = det_result.get("class_counts", {})
            inference_time = det_result.get("inference_time") or det_result.get("total_inference_time")
            
            parts = []
            if total_objects > 0:
                parts.append(f"检测完成！发现 {total_objects} 个目标。")
                if class_counts:
                    parts.append("各类别数量：")
                    for cls, cnt in class_counts.items():
                        parts.append(f"  - {cls}: {cnt}")
                if inference_time:
                    parts.append(f"推理耗时：{inference_time:.2f}ms")
                parts.append("请查看标注图了解详细检测结果。")
            else:
                parts.append("检测完成！未发现目标。")
            
            return {"final_response": "\n".join(parts)}

        if state.get("qa_result"):
            return {"final_response": state["qa_result"]}

        if state.get("analysis_result"):
            return {"final_response": state["analysis_result"]}

        return {"final_response": "抱歉，我没有理解您的请求，请重新描述。"}