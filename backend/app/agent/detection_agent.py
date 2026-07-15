"""
检测智能体（Day 11 升级版）— 多工具 Agent + 对话记忆 + 增强 SSE

升级内容（相比 Day 8）：
  1. Prompt 模板外置到 prompts.py
  2. 工具从 4 个扩展到 8 个（检测 4 + RAG 1 + 统计 2 + 用户 1）
  3. 集成对话记忆（Redis），支持跨轮次上下文
  4. SSE 事件协议增强（thinking/tool_start/tool_end/done/error）

架构：
  用户消息 → 加载历史 → Agent（LLM + 8 工具）→ 调用工具 → SSE 流式返回
"""

import json
from typing import AsyncGenerator, Optional

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import StructuredTool

from app.agent.memory import conversation_memory
from app.agent.prompts import DETECTION_AGENT_SYSTEM_PROMPT
from app.agent.tools.analysis_tool import ANALYSIS_TOOLS
from app.agent.tools.detection_tools import DETECTION_TOOLS
from app.agent.tools.knowledge_tool import KNOWLEDGE_TOOLS
from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


# ══════════════════════════════════════════════════════════════
# 一、创建 LLM 实例
# ══════════════════════════════════════════════════════════════


def create_llm():
    """
    根据配置创建 LLM 实例

    支持三种 LLM 后端：
      1. 通义千问（Qwen，通过 OpenAI 兼容接口）
      2. OpenAI（GPT-4o-mini）
      3. Ollama 本地部署
    """
    from langchain_openai import ChatOpenAI

    qwen_api_key = getattr(settings, "QWEN_API_KEY", "")
    if qwen_api_key and qwen_api_key != "sk-your-qwen-api-key":
        api_key = qwen_api_key
        base_url = getattr(
            settings, "QWEN_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        model_name = getattr(settings, "QWEN_MODEL", "qwen-plus")
    else:
        api_key = getattr(settings, "OPENAI_API_KEY", "")
        base_url = getattr(settings, "OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_name = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=0.1,
        streaming=True,
    )


# ══════════════════════════════════════════════════════════════
# 常量
# ══════════════════════════════════════════════════════════════

# 工具输出传给 LLM 的最大字符数（防止上下文超限）
MAX_TOOL_OUTPUT_CHARS = 2000
# 保存到对话记忆的 AI 回复最大字符数
MAX_MEMORY_TEXT_CHARS = 1500


def _truncate_tool_output(tool):
    """
    包装工具，截断其返回值，防止上下文超限

    LLM 只能看到截断后的结果，前端通过 SSE 事件获取完整结果。
    """
    original_func = tool.func

    def wrapped_func(*args, **kwargs):
        result = original_func(*args, **kwargs)
        result_str = str(result) if result is not None else ""
        if len(result_str) > MAX_TOOL_OUTPUT_CHARS:
            return result_str[:MAX_TOOL_OUTPUT_CHARS] + f"\n...[输出已截断，原始长度 {len(result_str)} 字符]"
        return result_str

    # 如果有 async func，也包装
    original_afunc = getattr(tool, 'coroutine', None)
    wrapped_afunc = None
    if original_afunc:
        async def async_wrapped_func(*args, **kwargs):
            result = await original_afunc(*args, **kwargs)
            result_str = str(result) if result is not None else ""
            if len(result_str) > MAX_TOOL_OUTPUT_CHARS:
                return result_str[:MAX_TOOL_OUTPUT_CHARS] + f"\n...[输出已截断，原始长度 {len(result_str)} 字符]"
            return result_str
        wrapped_afunc = async_wrapped_func

    return StructuredTool(
        name=tool.name,
        description=tool.description,
        func=wrapped_func,
        coroutine=wrapped_afunc,
        args_schema=tool.args_schema,
    )


# ══════════════════════════════════════════════════════════════
# 二、创建 ReAct Agent
# ══════════════════════════════════════════════════════════════


class DetectionAgent:
    """检测智能体（Day 11 升级版）"""

    def __init__(self):
        self.llm = create_llm()

        # ── 合并所有工具（检测 4 + RAG 1 + 统计 2 + 用户 1 = 8 个） ──
        raw_tools = DETECTION_TOOLS + ANALYSIS_TOOLS + KNOWLEDGE_TOOLS
        # 包装工具：截断输出，防止上下文超限
        self.all_tools = [_truncate_tool_output(t) for t in raw_tools]

        # ── 使用外置 Prompt 模板 ──
        prompt = ChatPromptTemplate.from_messages([
            ("system", DETECTION_AGENT_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.all_tools,
            prompt=prompt,
        )

        self.executor = AgentExecutor(
            agent=agent,
            tools=self.all_tools,
            verbose=True,
            max_iterations=8,  # 工具增多，适当提高迭代上限
            return_intermediate_steps=True,
        )

        logger.info(
            "DetectionAgent 初始化完成，绑定 %d 个工具（检测 %d + 分析 %d + 知识 %d）",
            len(self.all_tools),
            len(DETECTION_TOOLS),
            len(ANALYSIS_TOOLS),
            len(KNOWLEDGE_TOOLS),
        )

    async def chat_stream(
        self,
        message: str,
        user_id: int = 0,
        session_id: str = "default",
        image_path: Optional[str] = None,
    ) -> AsyncGenerator:
        """
        流式处理对话消息（增强版 SSE）

        Args:
            message: 用户文本消息
            user_id: 用户 ID
            session_id: 会话 ID
            image_path: 附带的图片路径（可选）

        Yields:
            SSE 事件数据字典
        """
        if image_path:
            message = f"{message}\n[附件图片路径: {image_path}]"

        # ── Step 1: 加载对话历史 ──
        chat_history = []
        try:
            history = conversation_memory.load_history(user_id, session_id)
            for msg in history:
                if msg["role"] == "user":
                    chat_history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "ai":
                    chat_history.append(AIMessage(content=msg["content"]))
        except Exception as e:
            logger.warning("加载对话历史失败: %s", str(e))

        # ── Step 2: 保存用户消息到记忆 ──
        try:
            conversation_memory.save_message(user_id, session_id, "user", message)
        except Exception as e:
            logger.warning("保存用户消息失败: %s", str(e))

        # ── Step 3: 发送 thinking 事件 ──
        yield {"type": "thinking", "content": "正在分析您的请求..."}

        # ── Step 4: 流式执行 Agent ──
        full_text = ""
        try:
            async for event in self.executor.astream_events(
                {"input": message, "chat_history": chat_history},
                version="v2",
            ):
                event_kind = event["event"]

                if event_kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        full_text += chunk.content
                        yield {
                            "type": "text_chunk",
                            "content": chunk.content,
                        }

                elif event_kind == "on_tool_start":
                    tool_name = event["name"]
                    tool_input = event["data"].get("input", {})
                    logger.info("工具调用: %s, 输入: %s", tool_name, str(tool_input)[:200])
                    yield {
                        "type": "tool_start",
                        "tool": tool_name,
                        "input": {k: str(v)[:100] for k, v in tool_input.items()},
                    }

                elif event_kind == "on_tool_end":
                    tool_data = event.get("data", {})
                    tool_output = tool_data.get("output", "")
                    tool_name = event.get("name", "")
                    result_str = str(tool_output) if tool_output else ""
                    summary = result_str[:100]
                    logger.info("工具完成: %s (输出 %d 字符)", tool_name, len(result_str))
                    yield {
                        "type": "tool_end",
                        "tool": tool_name,
                        "summary": summary,
                        "result": result_str,
                    }

        except Exception as e:
            logger.error("Agent 流式执行异常: %s", str(e), exc_info=True)
            yield {
                "type": "error",
                "content": f"处理出错：{str(e)}",
            }

        # ── Step 5: 保存 AI 回复到记忆（截断，防止上下文超限） ──
        if full_text:
            try:
                memory_text = full_text
                if len(full_text) > MAX_MEMORY_TEXT_CHARS:
                    memory_text = full_text[:MAX_MEMORY_TEXT_CHARS] + "\n...[回复已截断]"
                conversation_memory.save_message(user_id, session_id, "ai", memory_text)
            except Exception as e:
                logger.warning("保存 AI 回复失败: %s", str(e))

        # ── Step 6: 发送 done 事件 ──
        yield {
            "type": "done",
            "full_text": full_text,
        }

    async def chat(self, message: str, image_path: Optional[str] = None) -> dict:
        """非流式对话（兼容旧接口）"""
        if image_path:
            message = f"{message}\n[附件图片路径: {image_path}]"
        try:
            result = await self.executor.ainvoke({"input": message, "chat_history": []})
            return {
                "output": result["output"],
                "intermediate_steps": result.get("intermediate_steps", []),
            }
        except Exception as e:
            logger.error("Agent 执行异常: %s", str(e), exc_info=True)
            return {
                "output": f"抱歉，处理过程中出现错误：{str(e)}",
                "intermediate_steps": [],
            }


# 创建全局单例
detection_agent = DetectionAgent()
