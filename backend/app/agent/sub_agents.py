"""
子 Agent 节点函数 — LangGraph 状态图中的执行节点

每个节点函数接收 AgentState，运行自己的 ReAct Agent，
将结果写入 state.messages，供 LangGraph astream_events 捕获流式事件。

节点列表：
  - detection_agent_node: 检测子 Agent（4 个检测工具）
  - analysis_agent_node:  分析子 Agent（统计 + 历史 2 个工具）
  - qa_agent_node:        问答子 Agent（知识库 + 用户查询 2 个工具）
"""

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.agent.prompts import (
    ANALYSIS_SUB_AGENT_PROMPT,
    DETECTION_SUB_AGENT_PROMPT,
    QA_SUB_AGENT_PROMPT,
)
from app.agent.tools.analysis_tool import ANALYSIS_TOOLS
from app.agent.tools.detection_tools import DETECTION_TOOLS
from app.agent.tools.knowledge_tool import KNOWLEDGE_TOOLS
from app.core.logger import get_logger

logger = get_logger(__name__)


# 工具输出截断阈值（字符数）
_MAX_TOOL_OUTPUT = 8000


def _smart_truncate(text: str, max_len: int = _MAX_TOOL_OUTPUT) -> str:
    """智能截断：如果是 JSON，优先精简 detections 数组而非暴力截断"""
    if len(text) <= max_len:
        return text

    # 尝试作为 JSON 处理：保留结构，精简 detections 数组
    try:
        import json
        data = json.loads(text)
        if isinstance(data, dict) and "detections" in data:
            # 只保留前 5 条检测结果
            data["detections"] = data["detections"][:5]
            data["_truncated_note"] = f"已精简，原始 {len(text)} 字符"
            return json.dumps(data, ensure_ascii=False)
        if isinstance(data, dict) and "annotated_images" in data:
            # 批量检测：每张图片只保留前 3 条
            for img in data["annotated_images"]:
                if "detections" in img:
                    img["detections"] = img["detections"][:3]
            data["_truncated_note"] = f"已精简，原始 {len(text)} 字符"
            return json.dumps(data, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError, KeyError):
        pass

    # 非 JSON 或解析失败，暴力截断
    return text[:max_len] + f"\n...[已截断 {len(text)} 字符]"


def _wrap_tool(tool):
    """包装工具：截断超长返回值，防止 LLM 上下文超限"""
    from langchain_core.tools import StructuredTool

    orig = tool.func

    def _trunc(*a, **kw):
        r = str(orig(*a, **kw) or "")
        return _smart_truncate(r)

    afunc = getattr(tool, "coroutine", None)
    if afunc:
        async def _atrunc(*a, **kw):
            r = str(await afunc(*a, **kw) or "")
            return _smart_truncate(r)
    else:
        _atrunc = None

    return StructuredTool(
        name=tool.name,
        description=tool.description,
        func=_trunc,
        coroutine=_atrunc,
        args_schema=tool.args_schema,
    )


def _make_executor(llm, system_prompt, tools):
    """构建 ReAct AgentExecutor"""
    wrapped = [_wrap_tool(t) for t in tools]
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    agent = create_openai_tools_agent(llm=llm, tools=wrapped, prompt=prompt)
    return AgentExecutor(
        agent=agent,
        tools=wrapped,
        verbose=True,
        max_iterations=8,
        return_intermediate_steps=True,
    )


def _load_chat_history(state: dict) -> list:
    """从 state.messages 中提取历史消息（排除 system 消息）"""
    history = []
    for msg in state.get("messages", []):
        if isinstance(msg, HumanMessage):
            history.append(msg)
        elif isinstance(msg, AIMessage):
            history.append(msg)
    return history


# ══════════════════════════════════════════════════════════════
# 节点工厂：接收 LLM，返回节点函数闭包
# ══════════════════════════════════════════════════════════════


def make_detection_node(llm):
    """检测子 Agent 节点（4 个检测工具）"""
    executor = _make_executor(llm, DETECTION_SUB_AGENT_PROMPT, DETECTION_TOOLS)
    logger.info("Detection 子 Agent 初始化完成，工具: %d", len(DETECTION_TOOLS))

    async def detection_agent_node(state: dict) -> dict:
        user_msg = state["messages"][-1]
        chat_history = _load_chat_history(state)[:-1]  # 排除最后一条（当前消息）
        try:
            result = await executor.ainvoke(
                {"input": user_msg.content, "chat_history": chat_history}
            )
            output = result["output"]
        except Exception as e:
            logger.error("Detection Agent 执行失败: %s", e, exc_info=True)
            output = f"检测处理出错：{str(e)}"
        return {"messages": [AIMessage(content=output)], "detection_result": {"output": output}}

    return detection_agent_node


def make_analysis_node(llm):
    """分析子 Agent 节点（统计 + 历史 + 用户查询 3 个工具）"""
    executor = _make_executor(llm, ANALYSIS_SUB_AGENT_PROMPT, ANALYSIS_TOOLS)
    logger.info("Analysis 子 Agent 初始化完成，工具: %d", len(ANALYSIS_TOOLS))

    async def analysis_agent_node(state: dict) -> dict:
        user_msg = state["messages"][-1]
        chat_history = _load_chat_history(state)[:-1]
        try:
            result = await executor.ainvoke(
                {"input": user_msg.content, "chat_history": chat_history}
            )
            output = result["output"]
        except Exception as e:
            logger.error("Analysis Agent 执行失败: %s", e, exc_info=True)
            output = f"分析处理出错：{str(e)}"
        return {"messages": [AIMessage(content=output)], "analysis_result": {"output": output}}

    return analysis_agent_node


def make_qa_node(llm):
    """问答子 Agent 节点（知识库检索 + 用户查询 2 个工具）"""
    executor = _make_executor(llm, QA_SUB_AGENT_PROMPT, KNOWLEDGE_TOOLS)
    logger.info("QA 子 Agent 初始化完成，工具: %d", len(KNOWLEDGE_TOOLS))

    async def qa_agent_node(state: dict) -> dict:
        user_msg = state["messages"][-1]
        chat_history = _load_chat_history(state)[:-1]
        try:
            result = await executor.ainvoke(
                {"input": user_msg.content, "chat_history": chat_history}
            )
            output = result["output"]
        except Exception as e:
            logger.error("QA Agent 执行失败: %s", e, exc_info=True)
            output = f"问答处理出错：{str(e)}"
        return {"messages": [AIMessage(content=output)], "qa_result": output}

    return qa_agent_node
