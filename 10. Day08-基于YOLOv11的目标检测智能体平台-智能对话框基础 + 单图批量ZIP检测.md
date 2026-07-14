# Day 8：智能对话框基础 + 单图/批量/ZIP检测 — 详细教程

---

## 目录

- [一、今日目标与验收标准](#一今日目标与验收标准)
- [二、LangChain 核心概念速通](#二langchain-核心概念速通)
- [三、单 Agent 框架搭建（ReAct Agent + 多 Tool 绑定）](#三单-agent-框架搭建react-agent--多-tool-绑定)
- [四、DetectionService 实现（单图/批量/ZIP 检测）](#四detectionservice-实现单图批量zip-检测)
- [五、对话 SSE 流式接口 /api/chat/stream](#五对话-sse-流式接口-apichatstream)
- [六、检测工具定义（Agent 可调用的 Tools）](#六检测工具定义agent-可调用的-tools)
- [七、前端 ChatPage.vue — 对话界面实现](#七前端-chatpagevue--对话界面实现)
- [八、前端检测结果卡片组件](#八前端检测结果卡片组件)
- [九、快捷操作栏（双通道架构）](#九快捷操作栏双通道架构)
- [十、前后端联调测试](#十前后端联调测试)
- [十一、Day 8 里程碑验收](#十一day-8-里程碑验收)
- [十二、常见问题排查](#十二常见问题排查)
- [十三、Day 8 验收自查清单](#十三day-8-验收自查清单)

---

## 一、今日目标与验收标准

### 1.1 今日任务总览

Day 8 是**第三阶段"智能对话框 + 检测功能开发"的第一天**。在前面的阶段 阶段我们完成了数据采集、格式转换、模型训练、评估导出的完整闭环。今天我们将在已有模型之上，构建一个智能对话界面，让用户可以通过对话或快捷按钮触发目标检测，并以可视化卡片的形式展示检测结果。

今天的核心产出是：**一个支持自然语言触发 + 快捷按钮直调的双通道智能检测对话系统**。

| 时间段 | 内容 | 形式 |
| ------ | ---- | ---- |
| 上午 0.5h | LangChain 核心概念速通：Tool、Agent、Tool Calling 模式 | 讲授 |
| 上午 0.5h | 后端：单 Agent 框架搭建（ReAct Agent + 多 Tool 绑定） | 实操 |
| 上午 1h | 后端：DetectionService 实现（单图检测 + 批量检测 + ZIP 解压） | 实操 |
| 上午 1h | 后端：对话 SSE 流式接口 `/api/chat/stream` | 实操 |
| 下午 1.5h | 前端：ChatPage.vue 实现（消息气泡 + 文件附件上传 + 流式渲染） | 实操 |
| 下午 0.5h | 前端：检测结果卡片组件（标注图 + 目标统计表） | 实操 |
| 下午 0.5h | 前端：快捷操作栏（单图/批量/ZIP） | 实操 |
| 下午 0.5h | 联调：对话输入"检测这张图片" → Agent 调用 detect_single tool → 结果卡片 | 实操 |

### 1.2 验收标准

- [ ] 对话中可完成单图检测 + 批量检测（含 ZIP），结果以卡片形式展示
- [ ] 快捷按钮可直调检测 API（跳过 LLM，零延迟）
- [ ] 自然语言可触发检测（走 LLM Tool Calling 链路）
- [ ] 检测结果卡片可展示标注图 + 目标统计
- [ ] `backend/app/services/detection_service.py` 实现单图/批量/ZIP 检测
- [ ] `backend/app/api/chat.py` 实现 SSE 流式对话接口
- [ ] `backend/app/agent/detection_agent.py` 实现 ReAct Agent + 检测 Tool
- [ ] `frontend/src/views/ChatPage.vue` 完整对话界面
- [ ] `frontend/src/api/detection.js` 检测 API 封装

### 1.3 Day 8 结束后的目录结构（增量变化）

```
rsod-agent-platform/
├── backend/
│   ├── app/
│   │   ├── agent/                                    # 【新增】智能体模块
│   │   │   ├── __init__.py
│   │   │   └── detection_agent.py                    # 【新增】ReAct Agent + Tool 绑定
│   │   ├── api/
│   │   │   ├── chat.py                               # 【新增】对话 SSE 流式接口
│   │   │   ├── training.py                           # （已有）
│   │   │   └── auth.py                               # （已有）
│   │   ├── services/
│   │   │   ├── detection_service.py                  # 【新增】检测服务（单图/批量/ZIP）
│   │   │   └── user_service.py                       # （已有）
│   │   ├── config/
│   │   │   └── settings.py                           # 【更新】新增 LLM 相关配置
│   │   └── entity/
│   │       └── schemas.py                            # 【更新】新增对话相关 Schema
│   ├── main.py                                       # 【更新】注册 chat 路由
│   └── .env                                          # 【更新】新增 LLM API 密钥
│
├── frontend/
│   └── src/
│       ├── api/
│       │   └── detection.js                          # 【新增】检测 API 封装
│       ├── views/
│       │   └── ChatPage.vue                          # 【重写】完整对话界面
│       └── components/
│           └── DetectionResultCard.vue               # 【新增】检测结果卡片组件
│
└── docs/
    └── 基于YOLOv11的目标检测智能体平台-智能对话框基础 + 单图批量ZIP检测.md  # 本文档
```

---

## 二、LangChain 核心概念速通

### 2.1 为什么需要 LangChain？

在 Day 8 之前，我们的后端是传统的 REST API 模式：前端发送请求 → 后端 路由 → Service 层处理 → 返回 JSON。这对于"检测图片"这种确定性操作已经足够。

但我们的目标是构建一个**智能体平台**——用户可以用自然语言说"帮我检测一下这张图"、"分析一下最近的检测统计"，系统 需要理解用户意图、调用对应的工具、将结果包装成自然语言回复。

```
┌──────────────────────────────────────────────────────────────────┐
│                   传统 API vs Agent 对比                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  传统 REST API 模式：                                             │
│  ┌────────┐   POST /detect    ┌────────┐                        │
│  │ 前端   │ ───────────────→  │ 后端   │ → 固定路由 → 固定逻辑  │
│  └────────┘                   └────────┘                        │
│  问题：每个功能都要写死 API，无法灵活扩展                          │
│                                                                  │
│  Agent + Tool Calling 模式：                                      │
│  ┌────────┐  "检测这张图"   ┌────────┐  Tool Call  ┌─────────┐  │
│  │ 前端   │ ────────────→   │ Agent  │ ─────────→ │ detect  │  │
│  └────────┘                 │ (LLM)  │            │ _tool   │  │
│                             └────────┘            └─────────┘  │
│  优势：LLM 理解意图 → 自动选择工具 → 自然语言回复                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 核心概念三件套

```
┌──────────────────────────────────────────────────────────────────┐
│                LangChain 核心概念                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Tool（工具）                                                  │
│     ┌─────────────────────────────────────────────────┐          │
│     │ 一个可被 Agent 调用的函数，有明确的：              │          │
│     │   - name（名称）: "detect_objects"               │          │
│     │   - description（描述）: "检测图片中的目标"       │          │
│     │   - args_schema（参数模式）: {image_path: str}    │          │
│     │   - func（执行函数）: 实际调用 YOLO 推理          │          │
│     └─────────────────────────────────────────────────┘          │
│                                                                  │
│  2. Agent（智能体）                                               │
│     ┌─────────────────────────────────────────────────┐          │
│     │ 一个能"思考→行动→观察"的决策循环：                 │          │
│     │   - 思考（Thought）: 分析用户意图                 │          │
│     │   - 行动（Action）: 选择并调用 Tool              │          │
│     │   - 观察（Observation）: 读取 Tool 返回结果      │          │
│     │   - 回复（Final Answer）: 组织自然语言回复        │          │
│     └─────────────────────────────────────────────────┘          │
│                                                                  │
│  3. Tool Calling（工具调用）                                      │
│     ┌─────────────────────────────────────────────────┐          │
│     │ LLM 不 直接执行业务逻辑，而是：                    │          │
│     │   1. 理解用户说"检测这张图"                       │          │
│     │   2. 生成 Tool Call JSON:                        │          │
│     │      {"tool": "detect_objects",                  │          │
│     │       "args": {"image_path": "xxx.jpg"}}         │          │
│     │   3. 框架执行 Tool，获取结果                      │          │
│     │   4. LLM 将结果转化为自然语言回复                  │          │
│     └─────────────────────────────────────────────────┘          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 2.3 ReAct 模式

ReAct = **Re**asoning + **Act**ing。这是 Agent 最核心的思维模式：

```
用户输入: "帮我检测一下这张遥感图片"

循环开始：
  ┌───────────────────────────────────────────┐
  │ Thought: 用户想检测一张图片，需要调用      │
  │          detect_objects 工具               │
  │                                           │
  │ Action:  调用 detect_objects(             │
  │            image_path="remote_sense.jpg",  │
  │            conf=0.25)                     │
  │                                           │
  │ Observation: 工具返回了检测结果：           │
  │   检测到 5 个目标（3 架飞机, 2 个油罐）     │
  │                                           │
  │ Thought: 结果已获取，可以回复用户了         │
  │                                           │
  │ Final Answer: "检测完成！在这张遥感图片中   │
  │   发现了 5 个目标：3 架飞机（置信度 0.92）  │
  │   和 2 个储油罐（置信度 0.87）。"          │
  └───────────────────────────────────────────┘
```

### 2.4 本项目使用的 LLM

| 选项 | 说明 | 配置方式 |
| ---- | ---- | -------- |
| OpenAI GPT-4o-mini | 云端 API，效果最好，需付费 | `.env` 中配置 `OPENAI_API_KEY` |
| 通义千问 Qwen | 阿里云 API，国内访问快，有免费额度 | `.env` 中配置 `QWEN_API_KEY` |
| Ollama + Qwen2.5 | 本地部署，无需联网，但需要 GPU | `.env` 中配置 `USE_LOCAL_LLM=true` |

> **Day 8 推荐**：使用通义千问 Qwen（阿里云 `dashscope`），国内访问无需翻墙，免费额度充足，且 LangChain 已原生支持。

---

## 三、单 Agent 框架搭建（ReAct Agent + 多 Tool 绑定）

### 3.1 架构设计

Day 8 先搭建一个**单 Agent**（Day 11 再升级为 LangGraph 多 Agent 编排）。单 Agent 足够处理  单图/批量/ZIP 检测的需求。

```
┌────────────────────────────────────────────────────────────────┐
│                   单 Agent 架构                                  │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐                                             │
│  │   Chat API   │ ──→ 创建 ReAct Agent                        │
│  │ /api/chat/   │                                             │
│  │   stream     │                                             │
│  └──────┬───────┘                                             │
│         │                                                      │
│         ▼                                                      │
│  ┌──────────────┐     ┌──────────────────────┐                │
│  │   ReAct      │────→│  Detection Tool       │                │
│  │   Agent      │     │  - detect_single      │                │
│  │              │     │  - detect_batch       │                │
│  │  LLM 决策    │     │  - detect_zip         │                │
│  │  循环         │     └──────────────────────┘                │
│  └──────────────┘                                             │
│         │                                                      │
│         ▼                                                      │
│  ┌──────────────┐                                             │
│  │ Detection    │ ←── 实际执行 YOLO 推理                       │
│  │ Service      │                                             │
│  └──────────────┘                                             │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 3.2 Agent 模块初始化

文件：`backend/app/agent/__init__.py`

```python
"""
智能体模块
Day 8: 单 Agent (ReAct) + 检测工具
Day 11: 升级为 LangGraph 多 Agent 编排
"""
```

### 3.3 Detection Agent 实现

文件：`backend/app/agent/detection_agent.py`

```python
"""
检测智能体 — ReAct Agent + 检测工具绑定

职责：
  -. 创建 LangChain ReAct Agent
  - 绑定检测相关工具（单图/批量/ZIP）
  - 处理 SSE 流式输出 Agent 的思考过程和结果

架构：
  用户消息 → Agent（LLM 决策）→ 调用 DetectionTool → 返回 结果

使用方式：
  from app.agent.detection_agent import DetectionAgent

  agent = DetectionAgent()
  response = await agent.chat("检测这张图片", image_path="xxx.jpg")
"""

import json
from typing import AsyncGenerator

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.config.settings import settings
from app.core.logger import get_logger
from app.services.detection_service import detection_service

logger = get_logger(__name__)


# ══════════════════════════════════════════════════════════════
# 一、定义检测工具（Agent 可调用的 Tools）
# ══════════════════════════════════════════════════════════════


@tool
def detect_single_image(image_path: str, conf: float = 0.25, iou: float = 0.45) -> str:
    """
    检测单张图片中的目标物体。

    Args:
        image_path: 图片文件路径或 URL
        conf: 置信度阈值，默认 0.25
        iou: NMS IoU 阈值，默认 0.45

    Returns:
        JSON 字符串，包含检测结果（目标数量、类别统计、标注图路径）
    """
    result = detection_service.detect_single(image_path, conf=conf, iou=iou)
    return json.dumps(result, ensure_ascii=False)


@tool
def detect_batch_images(image_paths: list[str], conf: float = 0.25) -> str:
    """
    批量检测多张图片中的目标物体。

    Args:
        image_paths: 图片文件路径列表
        conf: 置信度阈值，默认 0.25

    Returns:
        JSON 字符串，包含每张图片的检测结果汇总
    """
    result = detection_service.detect_batch(image_paths, conf=conf)
    return json.dumps(result, ensure_ascii=False)


@tool
def detect_zip_images_file(zip_path: str, conf: float = 0.25) -> str:
    """
    解压 ZIP 文件并批量检测其中所有图片的目标物体。

    Args:
        zip_path: ZIP 文件路径
        conf: 置信度阈值，默认 0.25

    Returns:
        JSON 字符串，包含 ZIP 内所有图片的检测结果汇总
    """
    result = detection_service.detect_zip(zip_path, conf=conf)
    return json.dumps(result, ensure_ascii=False)


# 工具列表（绑定到 Agent）
DETECTION_TOOLS = [detect_single_image, detect_batch_images, detect_zip_images_file]


# ══════════════════════════════════════════════════════════════
# 二、创建 LLM 实例
# ══════════════════════════════════════════════════════════════


def create_llm():
    """
    根据配置创建 LLM 实例

    支持三种 LLM 后端：
      1. 通义千问（Qwen，通过 OpenAI 兼容接口）
      2. OpenAI（GPT-4o-mini）
      3. Ollama 本地部署
    """
    # 优先使用通义千问（国内访问快，有免费额度）
    qwen_api_key = getattr(settings, "QWEN_API_KEY", "")
    if qwen_api_key and qwen_api_key != "sk-your-qwen-api-key":
        api_key = qwen_api_key
        base_url = getattr(
            settings, "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        model_name = getattr(settings, "QWEN_MODEL", "qwen-plus")
    else:
        # 回退到 OpenAI
        api_key = getattr(settings, "OPENAI_API_KEY", "")
        base_url = getattr(settings, "OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_name = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=0.1,  # 低温度，减少随机性，检测结果需要确定性
    )


# ══════════════════════════════════════════════════════════════
# 三、创建 ReAct Agent
# ══════════════════════════════════════════════════════════════


class DetectionAgent:
    """检测智能体 — 封装 ReAct Agent 创建和对话逻辑"""

    def __init__(self):
        """初始化 Agent，创建 LLM 和 AgentExecutor"""
        self.llm = create_llm()

        # OpenAI Tools Agent 系统提示词
        system_prompt = """你是一个专业的目标检测助手。你可以帮用户检测图片中的目标物体。

重要规则：
- 当用户消息中包含 [附件图片路径: xxx] 时，xxx 就是图片的服务器路径，你应直接使用它调用检测工具
- 不要要求用户再次提供路径，直接使用附件中给出的路径
- 对于单张图片，调用 detect_single_image 工具
- 对于多张图片或 ZIP 文件，调用 detect_batch_images 或 detect_zip_images_file 工具

工作流程：
1. 理解用户意图
2. 如果有附件图片路径，直接调用检测工具
3. 调用工具获取检测结果
4. 用自然语言总结检测结果

回复格式要求：
- 先报告检测到的目标总数
- 列出各类别的数量统计
- 如果有标注图，告知用户可以在结果卡片中查看
- 简洁专业，不要过度解释"""

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        # 创建 OpenAI Tools Agent（与 ChatPromptTemplate + MessagesPlaceholder 完全兼容）
        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=DETECTION_TOOLS,
            prompt=prompt,
        )

        self.executor = AgentExecutor(
            agent=agent,
            tools=DETECTION_TOOLS,
            verbose=True,  # 开发阶段开启，可查看 Agent 思考过程
            max_iterations=5,  # 限制循环次数，防止无限循环
            return_intermediate_steps=True,  # 返回中间步骤（Tool 调用记录）
        )

        logger.info("DetectionAgent 初始化完成，绑定 %d 个工具", len(DETECTION_TOOLS))

    async def chat(self, message: str, image_path: str = None) -> dict:
        """
        处理用户对话消息

        Args:
            message: 用户文本消息
            image_path: 附带的图片路径（可选）

        Returns:
            Agent 响应字典
        """
        # 如果有图片附件，将路径信息追加到消息中
        if image_path:
            message = f"{message}\n[附件图片路径: {image_path}]"

        try:
            result = await self.executor.ainvoke({"input": message})

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

    async def chat_stream(self, message: str, image_path: str = None) -> AsyncGenerator:
        """
        流式处理对话消息（用于 SSE）

        逐个 yield Agent 的思考步骤和最终结果

        Args:
            message: 用户文本消息
            image_path: 附带的图片路径（可选）

        Yields:
            SSE 事件数据字典
        """
        if image_path:
            message = f"{message}\n[附件图片路径: {image_path}]"

        try:
            async for event in self.executor.astream_events(
                {"input": message},
                version="v2",
            ):
                event_kind = event["event"]

                if event_kind == "on_chat_model_stream":
                    # LLM 正在生成回复的文本片段
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        yield {
                            "type": "text_chunk",
                            "content": chunk.content,
                        }

                elif event_kind == "on_tool_start":
                    # Agent 开始调用工具
                    tool_name = event["name"]
                    tool_input = event["data"].get("input", {})
                    logger.info("工具调用: %s, 输入: %s", tool_name, str(tool_input)[:200])
                    yield {
                        "type": "tool_call",
                        "tool": tool_name,
                        "input": tool_input,
                    }

                elif event_kind == "on_tool_end":
                    # 工具调用完成
                    # 兼容不同 LangChain 版本的 output 路径
                    tool_data = event.get("data", {})
                    tool_output = tool_data.get("output", "")
                    tool_name = event.get("name", "")
                    logger.info(
                        "工具完成: %s, output类型=%s, output长度=%d",
                        tool_name,
                        type(tool_output).__name__,
                        len(str(tool_output)) if tool_output else 0,
                    )
                    # 记录 event data 的所有键，便于调试
                    logger.debug("on_tool_end data keys: %s", list(tool_data.keys()))
                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "result": str(tool_output) if tool_output else "",
                    }

        except Exception as e:
            logger.error("Agent 流式执行异常: %s", str(e), exc_info=True)
            yield {
                "type": "error",
                "content": f"处理出错：{str(e)}",
            }


# 创建全局单例
detection_agent = DetectionAgent()
```

### 3.4 配置更新

文件：`backend/app/config/settings.py`（更新部分）

```python
class Settings(BaseSettings):
    """应用全局配置"""

    # ... 已有配置 ...

    # ── LLM 配置 ──────────────────────────────────────
    OPENAI_API_KEY: str = "sk-your-api-key-here"
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # 通义千问（推荐，国内访问快）
    QWEN_API_KEY: str = "sk-your-qwen-api-key"
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen-plus"

    # ── 本地 LLM 配置（可选）──────────────────────
    USE_LOCAL_LLM: bool = False
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
```

文件：`backend/.env`（新增配置）

```bash
# ── LLM 配置（Day 8 新增）───────────────────────
# 通义千问（推荐）
QWEN_API_KEY=sk-your-qwen-api-key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# OpenAI（备选）
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 3.5 注册路由

文件：`backend/main.py`（更新部分）

```python
# 新增导入
from app.api.chat import router as chat_router
from app.api.detection import router as detection_router

# 注册路由
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(training_router)
app.include_router(chat_router)  # Day 8 新增
app.include_router(detection_router) # Day 8 新增
```

---

## 四、DetectionService 实现（单图/批量/ZIP 检测）

### 4.1 架构设计

DetectionService 是检测功能的核心服务层，被 Agent Tool 和快捷按钮 API 共同调用。

```
┌────────────────────────────────────────────────────────────────┐
│                 DetectionService 调用关系                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  调用方 1: Agent Tool（自然语言触发）                             │
│    "检测这张图片" → Agent → detect_single_image tool            │
│                              ↓                                 │
│  调用方 2: 快捷按钮 API（直接调用）                               │
│    POST /api/detection/single → 直接调用                        │
│                              ↓                                 │
│                    ┌──────────────────┐                         │
│                    │ DetectionService │                         │
│                    │                  │                         │
│                    │ - detect_single  │                         │
│                    │ - detect_batch   │                         │
│                    │ - detect_zip     │                         │
│                    └────────┬─────────┘                         │
│                             ↓                                  │
│                    ┌──────────────────┐                         │
│                    │  YOLO 推理引擎    │                         │
│                    │  (ultralytics)   │                         │
│                    └────────┬─────────┘                         │
│                             ↓                                  │
│                    ┌──────────────────┐                         │
│                    │ MinIO 存储标注图  │                         │
│                    │ PostgreSQL 存结果 │                         │
│                    └──────────────────┘                         │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 4.2 DetectionService 实现

文件：`backend/app/services/detection_service.py`

```python
"""
目标检测服务 — 封装 YOLOv11 推理逻辑

职责：
  - 单图检测（detect_single）
  - 批量检测（detect_batch）
  - ZIP 解压 + 批量检测（detect_zip）
  - 结果持久化（MinIO 存储标注图 + PostgreSQL 存储检测结果）

架构：
  DetectionService 是无状态的纯服务，被 Agent Tool 和快捷按钮 API 共同调用。
  每次检测都会：
    1. 创建 DetectionTask 记录
    2. 运行 YOLO 推理
    3. 上传 标注图到 MinIO
    4. 保存 DetectionResult 记录

使用方式：
  from app.services.detection_service import detection_service

  result = detection_service.detect_single(image_path, scene_id, user_id)
"""

import base64
import os
import tempfile
import zipfile
from datetime import datetime

import cv2
from sqlalchemy.orm import Session
from ultralytics import YOLO

from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import (
    DetectionResult,
    DetectionScene,
    DetectionTask,
    ModelVersion,
)
from app.storage.minio_client import MinIOClient

logger = get_logger(__name__)

# ── 支持的图片格式 ──
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/bmp",
    "image/webp",
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
}


class DetectionService:
    """目标检测服务 — 封装 YOLOv11 推理全流程"""

    @staticmethod
    def _get_default_model_path() -> str:
        """
        获取默认模型权重路径

        查找顺序：
          1. models/ 目录下 is_default=True 的模型
          2. runs/train/ 目录下最新训练产出的 best.pt
          3. 回退到预训练模型 yolov11n.pt
        """
        db = SessionLocal()
        try:
            # 查找默认模型版本
            default_model = (
                db.query(ModelVersion).filter(ModelVersion.is_default == True).first()
            )
            if default_model and os.path.exists(default_model.model_path):
                return default_model.model_path

            # 回退：查找最新训练的 best.pt
            from app.entity.db_models import TrainingTask

            latest_task = (
                db.query(TrainingTask)
                .filter(TrainingTask.status == "completed")
                .order_by(TrainingTask.completed_at.desc())
                .first()
            )
            if latest_task:
                weights_path = os.path.join(
                    os.getcwd(),
                    settings.TRAIN_OUTPUT_DIR,
                    f"task_{latest_task.task_uuid}",
                    "weights",
                    "best.pt",
                )
                if os.path.exists(weights_path):
                    return weights_path
        finally:
            db.close()

        # 最终回退：预训练模型
        return "yolo11n.pt"

    @staticmethod
    def _get_model(scene_id: int = None) -> YOLO:
        """
        加载 YOLO 模型

        优先使用场景关联的默认模型，否则使用全局默认模型
        """
        model_path = None

        if scene_id:
            db = SessionLocal()
            try:
                default_model = (
                    db.query(ModelVersion)
                    .filter(
                        ModelVersion.scene_id == scene_id,
                        ModelVersion.is_default == True,
                    )
                    .first()
                )
                if default_model and os.path.exists(default_model.model_path):
                    model_path = default_model.model_path
            finally:
                db.close()

        if not model_path:
            model_path = DetectionService._get_default_model_path()

        logger.info("加载检测模型: %s", model_path)
        return YOLO(model_path)

    @staticmethod
    def _save_task_and_results(
        db: Session,
        user_id: int,
        scene_id: int,
        task_type: str,
        detections: list,
        annotated_image: bytes,
        original_filename: str,
        inference_time: float,
        conf: float,
        iou: float,
    ) -> dict:
        """
        保存检测任务和结果到数据库 + MinIO

        Returns:
            包含 task_id 和 annotated_image_url 的字典
        """
        # ── 创建检测任务记录 ──
        task = DetectionTask(
            user_id=user_id,
            scene_id=scene_id,
            task_type=task_type,
            status="completed",
            total_images=1,
            total_objects=len(detections),
            total_inference_time=inference_time,
            conf_threshold=conf,
            iou_threshold=iou,
            completed_at=datetime.now(),
        )
        db.add(task)
        db.flush()  # 获取 task.id

        # ── 上传 标注图到 MinIO ──
        annotated_image_url = None
        try:
            minio_client = MinIOClient()
            object_name = f"detections/{task.id}/{original_filename}"
            annotated_image_url = minio_client.upload_bytes(
                object_name, annotated_image, "image/jpeg"
            )
            task.annotated_image_url = annotated_image_url  # 修正：这里应该更新的是 annotated_image_url 字段，但这个字段不存在于 DetectionTask 中
        except Exception as e:
            logger.warning("MinIO 上传失败（不影响检测结果）: %s", str(e))

        # ── 保存每条检测结果 ──
        for det in detections:
            result = DetectionResult(
                task_id=task.id,
                image_path=original_filename,
                annotated_image_url=annotated_image_url,
                class_name=det["class_name"],
                class_name_cn=det.get("class_name_cn"),
                class_id=det["class_id"],
                confidence=det["confidence"],
                bbox=det["bbox"],
                inference_time=inference_time,
            )
            db.add(result)

        db.commit()
        return {"task_id": task.id, "annotated_image_url": annotated_image_url}

    def detect_single(
        self,
        image_path: str,
        conf: float = 0.25,
        iou: float = 0.45,
        scene_id: int = None,
        user_id: int = None,
    ) -> dict:
        """
        单图检测

        Args:
            image_path: 图片文件路径
            conf: 置信度阈值
            iou: NMS IoU 阈值
            scene_id: 检测场景 ID
            user_id: 操作用户 ID

        Returns:
            检测结果字典：
            {
                "total_objects": int,
                "class_counts": {"class_name": count, ...},
                "detections": [...],
                "annotated_image_base64": str,
                "inference_time": float,
                "task_id": int,
            }
        """
        db = SessionLocal()
        try:
            # ── 加载模型 ──
            model = self._get_model(scene_id)

            # ── YOLO 推理 ──
            results = model.predict(
                source=image_path,
                conf=conf,
                iou=iou,
                imgsz=640,
                device="cpu",
                save=False,
                verbose=False,
            )

            result = results[0]
            detections = []
            total_objects = 0

            if result.boxes is not None and len(result.boxes) > 0:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = model.names.get(cls_id, f"class_{cls_id}")
                    confidence = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].tolist()

                    detections.append(
                        {
                            "class_name": cls_name,
                            "class_id": cls_id,
                            "confidence": round(confidence, 4),
                            "bbox": [
                                round(x1, 1),
                                round(y1, 1),
                                round(x2, 1),
                                round(y2, 1),
                            ],
                        }
                    )
                    total_objects += 1

            # ── 生成标注图 ──
            annotated_img = result.plot()
            _, buffer = cv2.imencode(
                ".jpg", annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 85]
            )
            annotated_base64 = base64.b64encode(buffer).decode("utf-8")

            # ── 统计各类别数量 ──
            class_counts = {}
            for det in detections:
                name = det["class_name"]
                class_counts[name] = class_counts.get(name, 0) + 1

            # ── 持久化到数据库 ──
            task_id = None
            annotated_image_url = None
            if user_id and scene_id:
                save_result = self._save_task_and_results(
                    db=db,
                    user_id=user_id,
                    scene_id=scene_id,
                    task_type="single",
                    detections=detections,
                    annotated_image=buffer.tobytes(),
                    original_filename=os.path.basename(image_path),
                    inference_time=float(result.speed.get("inference", 0)),
                    conf=conf,
                    iou=iou,
                )
                task_id = save_result["task_id"]
                annotated_image_url = save_result.get("annotated_image_url")

            logger.info(
                "单图检测完成: %s, 检测到 %d 个目标, 耗时 %.2fms",
                image_path,
                total_objects,
                float(result.speed.get("inference", 0)),
            )

            return {
                "total_objects": total_objects,
                "class_counts": class_counts,
                "detections": detections,
                "annotated_image_base64": annotated_base64,
                "annotated_image_url": annotated_image_url,
                "inference_time": round(float(result.speed.get("inference", 0)), 2),
                "task_id": task_id,
            }

        except Exception as e:
            logger.error("单图检测异常: %s", str(e), exc_info=True)
            return {"error": f"检测失败: {str(e)}"}
        finally:
            db.close()

    def detect_batch(
        self,
        image_paths: list[str],
        conf: float = 0.25,
        scene_id: int = None,
        user_id: int = None,
    ) -> dict:
        """
        批量检测多张图片

        Args:
            image_paths: 图片文件路径列表
            conf: 置信度阈值
            scene_id: 检测场景 ID
            user_id: 操作用户 ID

        Returns:
            批量检测结果字典
        """
        db = SessionLocal()
        try:
            model = self._get_model(scene_id)

            # 当 scene_id 为 None 时，自动查询第一个可用场景
            if not scene_id:
                default_scene = db.query(DetectionScene).first()
                if default_scene:
                    scene_id = default_scene.id
                else:
                    return {"error": "数据库中没有可用的检测场景，请先创建检测场景"}

            # ── 创建批量检测任务 ──
            task = DetectionTask(
                user_id=user_id or 0,
                scene_id=scene_id,
                task_type="batch",
                status="processing",
                total_images=len(image_paths),
                conf_threshold=conf,
            )
            db.add(task)
            db.flush()

            all_detections = []
            annotated_images = []  # 每张图片的标注图 base64
            total_objects = 0
            total_inference_time = 0
            class_counts = {}

            for i, image_path in enumerate(image_paths):
                results = model.predict(
                    source=image_path,
                    conf=conf,
                    iou=0.45,
                    imgsz=640,
                    device="cpu",
                    save=False,
                    verbose=False,
                )
                result = results[0]
                inference_time = float(result.speed.get("inference", 0))
                total_inference_time += inference_time

                # 生成标注图 base64
                annotated_img = result.plot()
                _, buffer = cv2.imencode(
                    ".jpg", annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 85]
                )
                annotated_images.append({
                    "image_path": os.path.basename(image_path),
                    "annotated_image_base64": base64.b64encode(buffer).decode("utf-8"),
                })

                if result.boxes is not None and len(result.boxes) > 0:
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        cls_name = model.names.get(cls_id, f"class_{cls_id}")
                        confidence = float(box.conf[0])
                        x1, y1, x2, y2 = box.xyxy[0].tolist()

                        det = {
                            "image_path": image_path,
                            "class_name": cls_name,
                            "class_id": cls_id,
                            "confidence": round(confidence, 4),
                            "bbox": [
                                round(x1, 1),
                                round(y1, 1),
                                round(x2, 1),
                                round(y2, 1),
                            ],
                            "inference_time": inference_time,
                        }
                        all_detections.append(det)
                        total_objects += 1

                        # 统计类别计数
                        class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

                    # 保存检测结果到数据库
                    for det in all_detections:
                        if det["image_path"] == image_path:
                            db_result = DetectionResult(
                                task_id=task.id,
                                image_path=image_path,
                                class_name=det["class_name"],
                                class_id=det["class_id"],
                                confidence=det["confidence"],
                                bbox=det["bbox"],
                                inference_time=inference_time,
                            )
                            db.add(db_result)

            task.status = "completed"
            task.total_objects = total_objects
            task.total_inference_time = total_inference_time
            task.completed_at = datetime.now()
            db.commit()

            logger.info(
                "批量检测完成: %d 张图, 共 %d 个目标, 总耗时 %.2fms",
                len(image_paths),
                total_objects,
                total_inference_time,
            )

            return {
                "task_id": task.id,
                "total_images": len(image_paths),
                "total_objects": total_objects,
                "class_counts": class_counts,
                "total_inference_time": round(total_inference_time, 2),
                "detections": all_detections,
                "annotated_images": annotated_images,
            }

        except Exception as e:
            logger.error("批量检测异常: %s", str(e), exc_info=True)
            return {"error": f"批量检测失败: {str(e)}"}
        finally:
            db.close()

    def detect_zip(
        self,
        zip_path: str,
        conf: float = 0.25,
        scene_id: int = None,
        user_id: int = None,
    ) -> dict:
        """
        解压 ZIP 文件并批量检测其中所有图片

        Args:
            zip_path: ZIP 文件路径
            conf: 置信度阈值
            scene_id: 检测场景 ID
            user_id: 操作用户 ID

        Returns:
            ZIP 检测结果字典
        """
        temp_dir = None
        try:
            # ── 解压 ZIP 到临时目录 ──
            temp_dir = tempfile.mkdtemp(prefix="rsod_zip_")
            logger.info("解压 ZIP 文件: %s → %s", zip_path, temp_dir)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(temp_dir)

            # ── 筛选图片文件 ──
            image_files = []
            for root, dirs, files in os.walk(temp_dir):
                for fname in files:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                        image_files.append(os.path.join(root, fname))

            if not image_files:
                return {"error": "ZIP 文件中没有找到图片"}

            logger.info("ZIP 中包含 %d 张图片，开始批量检测", len(image_files))

            # ── 调用批量检测 ──
            batch_result = self.detect_batch(
                image_paths=image_files,
                conf=conf,
                scene_id=scene_id,
                user_id=user_id,
            )

            batch_result["source"] = "zip"
            batch_result["zip_filename"] = os.path.basename(zip_path)
            batch_result["total_images_in_zip"] = len(image_files)

            return batch_result

        except zipfile.BadZipFile:
            return {"error": f"无效的 ZIP 文件: {zip_path}"}
        except Exception as e:
            logger.error("ZIP 检测异常: %s", str(e), exc_info=True)
            return {"error": f"ZIP 检测失败: {str(e)}"}
        finally:
            # ── 清理临时目录 ──
            if temp_dir and os.path.exists(temp_dir):
                import shutil

                shutil.rmtree(temp_dir, ignore_errors=True)


# 创建全局单例
detection_service = DetectionService()
```

### 4.3 更新 requirements.txt

文件：`backend/requirements.txt`（确认已有依赖）

```
# Day 8 所需的关键依赖（已存在于 requirements.txt 中）：
# - ultralytics==8.3.0       ← YOLO 推理引擎
# - opencv-python==4.8.0.76  ← 图像处理（cv2.imencode 等）
# - Pillow==10.0.0           ← 图像处理备选
# - langchain==0.3.0         ← Agent 框架
# - langchain-openai==0.2.0  ← LLM 调用
# - langgraph==0.3.0         ← Day 11 多 Agent 编排时使用
# - openai==1.50.0           ← OpenAI / 通义千问兼容接口
```

---

## 五、对话 SSE 流式接口 /api/chat/stream

### 5.1 SSE 协议说明

SSE（Server-Sent Events）是一种服务端向客户端单向推送数据的协议。相比 WebSocket，SSE 更轻量，适合"请求-流式响应"的场景。

```
┌────────────────────────────────────────────────────────────┐
│                    SSE 数据流格式                             │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  HTTP/1.1 200 OK                                          │
│  Content-Type: text/event-stream                           │
│                                                            │
│  data: {"type":"text_chunk","content":"好的"}              │
│                                                            │
│  data: {"type":"tool_call","tool":"detect_single",...}     │
│                                                            │
│  data: {"type":"tool_result","result":{...}}               │
│                                                            │
│  data: {"type":"text_chunk","content":"检测到3个目标"}     │
│                                                            │
│  data: [DONE]                                              │
│                                                            │
└────────────────────────────────────────────────────────────┘

每条消息以 "data: " 开头，以 "\n\n" 分隔。
流结束标志：data: [DONE]
```

### 5.2 Chat API 实现

文件：`backend/app/api/chat.py`

```python
"""
对话相关 API 路由

接口列表：
  - POST /api/chat/upload    上传图片文件，返回服务端路径
  - POST /api/chat/stream    SSE 流式对话（核心接口）

"""

import json
import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.agent.detection_agent import detection_agent
from app.api.auth import get_current_user
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["智能对话"])

# 上传文件临时存储目录
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "rsod_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", summary="上传图片文件")
async def upload_image(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """
    上传图片文件到服务端临时目录

    Returns:
        { "image_path": "/tmp/rsod_uploads/xxx.jpg" }
    """
    suffix = os.path.splitext(file.filename)[1] or ".jpg"
    # 使用原始文件名保存到临时目录
    filename = f"{os.getpid()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    logger.info("图片上传成功: %s → %s", file.filename, file_path)
    return {"image_path": file_path}


@router.post("/stream")
async def chat_stream(
    request: Request,
    current_user=Depends(get_current_user),
):
    """
    SSE 流式对话接口

    请求体：
    {
        "message": "检测这张图片",
        "image_path": "/tmp/uploads/xxx.jpg",  // 可选，快捷按钮传入
        "session_id": 123                        // 可选，会话 ID
    }

    响应：SSE 流式事件
    """
    # ── 解析请求体 ──
    body = await request.json()
    message = body.get("message", "")
    image_path = body.get("image_path")
    session_id = body.get("session_id")

    if not message:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    logger.info(
        "用户 %s 发起对话: message=%s, image=%s",
        current_user.username,
        message[:50],
        "有" if image_path else "无",
    )

    # ── SSE 流式响应 ──
    async def event_generator():
        try:
            # 使用 Agent 流式处理
            async for event in detection_agent.chat_stream(
                message=message,
                image_path=image_path,
            ):
                # 将事件序列化为 SSE 格式
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

            # 流结束标志
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("SSE 流异常: %s", str(e), exc_info=True)
            error_data = json.dumps(
                {"type": "error", "content": str(e)},
                ensure_ascii=False,
            )
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁止 Nginx 缓冲 SSE
        },
    )
```

### 5.3 SSE 接口测试

使用 curl 测试（需要先登录获取 Token）：

```bash
# 1. 登录获取 Token（Swagger UI中获取）

# 2. 测试 SSE 流式对话
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"你好，请介绍一下自己"}'
```

预期输出：

```
data: {"type":"text_chunk","content":"你好"}

data: {"type":"text_chunk","content":"！我是 RSOD"}

data: {"type":"text_chunk","content":"":"目标检测智能体平台的"}

data: {"type":"text_chunk","content":"AI 助手。"}

data: [DONE]
```

### 5.4 Vite Proxy 配置

文件：`frontend/vite.config.js`（确认 SSE 代理配置）

```javascript
export default defineConfig({
  //: 已有配置 ...

  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

> **注意**：SSE 流式请求使用原生 `fetch` + `ReadableStream`（见 `frontend/src/utils/stream.js`），不走 Axios，因为 Axios 不支持流式读取。

---

## 六、检测工具定义（Agent 可调用的 Tools）

### 6.1 工具注册流程

```
┌────────────────────────────────────────────────────────────────┐
│                    Tool 注册流程                                 │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  1. 定义 @tool 函数                                             │
│     ┌──────────────────────────────────┐                       │
│     │ @tool                            │                       │
│     │ def detect_single_image(         │                       │
│     │     image_path: str,             │                       │
│     │     conf: float = 0.25           │                       │
│     │ ) -> str:                        │                       │
│     │     """检测单张图片"""             │                       │
│     │     ...                          │                       │
│     └──────────────────────────────────┘                       │
│                                                                │
│  2. 注册到工具列表                                              │
│     DETECTION_TOOLS = [                                        │
│         detect_single_image,                                   │
│         detect_batch_images,                                   │
│         detect_zip_file,                                       │
│     ]                                                          │
│                                                                │
│  3. 绑定到 Agent                                                │
│     agent = create_react_agent(                                │
│         llm=llm,                                               │
│         tools=DETECTION_TOOLS,                                 │
│         prompt=prompt,                                         │
│     )                                                          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 6.2 工具参数说明

| 工具 | 参数 | 类型 | 说明 |
| ---- | ---- | ---- | ---- |
| `detect_single_image` | `image_path` | `str` | 图片文件路径 |
| | `conf` | `float` | 置信度阈值（默认 0.25） |
| | `iou` | `float` | NMS IoU 阈值（默认 0.45） |
| `detect_batch_images` | `image_paths` | `list[str]` | 图片路径列表 |
| | `conf` | `float` | 置信度阈值（默认 0.25） |
| `detect_zip_file` | `zip_path` | `str` | ZIP 文件路径 |
| | `conf` | `float` | 置信度阈值（默认 0.25） |

> **重要**：`@tool` 装饰器会自动从函数的 docstring 和类型注解中提取工具描述，LLM 通过这些描述来理解工具的功能并决定何时调用。所以 docstring 必须清晰准确。

---

## 七、前端 ChatPage.vue — 对话界面实现

### 7.1 页面架构

```
┌────────────────────────────────────────────────────────────────┐
│                      ChatPage.vue 布局                          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                   消息列表区域                           │    │
│  │                                                        │    │
│  │  ┌──────────────────────────────────────┐              │    │
│  │  │ 🤖 AI: 你好！我是 RSOD 检测助手       │  ← assistant │    │
│  │  └──────────────────────────────────────┘              │    │
│  │                                                        │    │
│  │  ┌──────────────────────────────────────┐              │    │
│  │  │ 👤 用户: 检测这张图片                  │  ← user     │    │
│  │  │    [📎 test.jpg]                     │              │    │
│  │  └──────────────────────────────────────┘              │    │
│  │                                                        │    │
│  │  ┌──────────────────────────────────────┐              │    │
│  │  │ 🤖 AI: 正在检测中...                   │  ← loading  │    │
│  │  └──────────────────────────────────────┘              │    │
│  │                                                        │    │
│  │  ┌──────────────────────────────────────┐              │    │
│  │  │ 🤖 AI: 检测完成！发现 5 个目标        │  ← result   │    │
│  │  │ ┌──────────────────────────────┐     │              │    │
│  │  │ │   [标注图预览]                │     │  ← 卡片     │    │
│  │  │ │   飞机: 3  油罐: 2            │     │              │    │
│  │  │ └──────────────────────────────┘     │              │    │
│  │  └──────────────────────────────────────┘              │    │
│  │                                                        │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  快捷操作栏                                             │    │
│  │  [📷 单图检测] [📁 批量/ZIP] [🎬 视频] [📹 摄像头]     │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  输入区                                                 │    │
│  │  [📎] [请输入消息...                    ] [发送/停止]   │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 7.2 ChatPage.vue 完整实现

文件：`frontend/src/views/ChatPage.vue`

```vue
<template>
  <div class="chat-page">
    <!-- ── 消息列表区域 ── -->
    <div class="message-list" ref="messageListRef">
      <div
        v-for="(msg, index) in agentStore.messages"
        :key="index"
        :class="['message-item', `message-${msg.role}`]"
      >
        <!-- 用户消息 -->
        <div v-if="msg.role === 'user'" class="message-bubble user-bubble">
          <div class="message-content">{{ msg.content }}</div>
          <!-- 单张图片附件 -->
          <div v-if="msg.image" class="message-attachment">
            <img :src="msg.imagePreview" alt="附件图片" />
          </div>
          <!-- 多图附件（批量检测） -->
          <div v-if="msg.images && msg.images.length" class="message-attachments-grid">
            <img v-for="(src, i) in msg.images" :key="i" :src="src" alt="附件图片" />
          </div>
        </div>

        <!-- AI 消息 -->
        <div
          v-else-if="msg.role === 'assistant'"
          class="message-bubble assistant-bubble"
        >
          <div v-if="msg.loading" class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
          <div
            v-else
            class="message-content markdown-body"
            v-html="renderMarkdown(msg.content)"
          ></div>

          <!-- 检测结果卡片 -->
          <DetectionResultCard
            v-if="msg.detectionResult"
            :result="msg.detectionResult"
          />
        </div>

        <!-- 工具调用提示 -->
        <div v-if="msg.toolCall" class="tool-call-info">
          <el-tag size="small" type="info">
            🔧 调用工具: {{ msg.toolCall.tool }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- ── 快捷操作栏 ── -->
    <div class="quick-actions">
      <el-button
        @click="handleQuickDetect('single')"
        :disabled="agentStore.isLoading"
      >
        📷 单图检测
      </el-button>
      <el-button
        @click="handleQuickDetect('batch')"
        :disabled="agentStore.isLoading"
      >
        📁 批量/ZIP
      </el-button>
      <el-button disabled>🎬 视频</el-button>
      <el-button disabled>📹 摄像头</el-button>
    </div>

    <!-- ── 输入区域 ── -->
    <div class="input-area">
      <!-- 附件按钮 -->
      <el-button
        class="attach-btn"
        @click="triggerFileInput"
        :disabled="agentStore.isLoading"
        circle
      >
        📎
      </el-button>
      <input
        ref="fileInputRef"
        type="file"
        accept="image/*,.zip"
        style="display: none"
        @change="handleFileSelect"
      />

      <!-- 文本输入框 -->
      <el-input
        v-model="inputText"
        placeholder="输入消息，或拖拽图片/ZIP 到这里..."
        @keyup.enter="sendMessage"
        :disabled="agentStore.isLoading"
      />

      <!-- 发送/停止按钮 -->
      <el-button
        v-if="!agentStore.isLoading"
        type="primary"
        @click="sendMessage"
        :disabled="!inputText.trim() && !selectedFile"
      >
        发送
      </el-button>
      <el-button v-else type="danger" @click="handleStop"> 停止 </el-button>
    </div>
  </div>
</template>

<script setup>
/**
 * ChatPage.vue — 智能对话界面
 *
 * 功能：
 *   - 消息气泡（用户/AI 区分）
 *   - 文件附件上传（图片/ZIP 拖拽或选择）
 *   - SSE 流式渲染 AI 回复
 *   - 检测结果卡片展示
 *   - 快捷操作栏（单图/批量/视频/摄像头）
 *   - 中断当前对话
 */
import { detectBatch, detectSingle, detectZip } from "@/api/detection";
import DetectionResultCard from "@/components/DetectionResultCard.vue";
import { useAgentStore } from "@/stores/agent";
import { renderMarkdown } from "@/utils/markdown";
import request from "@/utils/request";
import { streamChat } from "@/utils/stream";
import { ElMessage } from "element-plus";
import { computed, nextTick, onMounted, ref } from "vue";

// ── Store ──
const agentStore = useAgentStore();

// ── 响应式状态 ──
const inputText = ref("");
const selectedFile = ref(null);
const messageListRef = ref(null);
const fileInputRef = ref(null);

// ── 计算属性 ──
const canSend = computed(() => {
  return inputText.value.trim() || selectedFile.value;
});

// ── 方法 ──

/** 发送消息 */
async function sendMessage() {
  if (!canSend.value) return;

  const message = inputText.value.trim();
  // ── 关键：在清空之前保存文件引用 ──
  const fileToSend = selectedFile.value;
  const imagePreview = fileToSend ? URL.createObjectURL(fileToSend) : null;

  // 添加用户消息到列表
  agentStore.addMessage({
    role: "user",
    content: message,
    image: fileToSend ? fileToSend.name : null,
    imagePreview,
  });

  // 清空输入
  inputText.value = "";
  selectedFile.value = null;

  // 添加 AI 加载占位
  agentStore.addMessage({
    role: "assistant",
    content: "",
    loading: true,
  });

  // 滚动到底部
  scrollToBottom();

  // ── 如果有附件图片，先上传到服务端获取真实路径 ──
  let serverImagePath = null;
  if (fileToSend) {
    try {
      const formData = new FormData();
      formData.append("file", fileToSend);
      // 不设置 Content-Type，让 axios 自动添加 boundary
      const uploadResult = await request.post("/chat/upload", formData);
      serverImagePath = uploadResult.image_path;
    } catch (err) {
      console.error("[图片上传失败]", err.response?.data || err.message || err);
      const lastMsg = agentStore.messages[agentStore.messages.length - 1];
      lastMsg.content = `图片上传失败：${err.response?.data?.detail || err.message || "未知错误"}，请重试`;
      lastMsg.loading = false;
      lastMsg.error = true;
      return;
    }
  }

  // 发起 SSE 流式请求
  const requestBody = {
    message,
    ...(serverImagePath ? { image_path: serverImagePath } : {}),
  };

  let fullContent = "";

  const stop = streamChat("/api/chat/stream", requestBody, {
    onMessage: (data) => {
      // 调试日志：查看收到的所有 SSE 事件
      console.log("[SSE事件]", data.type, data.type === "tool_result" ? data : "");

      if (data.type === "text_chunk") {
        fullContent += data.content;
        agentStore.updateLastAssistantMessage(fullContent);
        scrollToBottom();
      } else if (data.type === "tool_call") {
        // 工具调用中，更新最后一条 AI 消息的工具信息
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.toolCall = { tool: data.tool, input: data.input };
      } else if (data.type === "tool_result") {
        // 工具调用返回结果
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        console.log("[工具结果] tool:", data.tool, "result长度:", data.result?.length);
        try {
          const result = JSON.parse(data.result);
          console.log("[工具结果解析]", "total_objects:", result.total_objects, "detections:", result.detections?.length);
          if (result.detections) {
            // 有检测结果，设置到消息中
            lastMsg.detectionResult = result;
            lastMsg.loading = false;
            console.log("[检测结果卡片已设置]", lastMsg.detectionResult);
          }
        } catch (e) {
          console.warn("[工具结果解析失败]", e.message, "原始数据:", data.result?.substring(0, 200));
          // 非检测结果 JSON，作为普通文本
          lastMsg.content += `\n[工具结果: ${data.result?.substring(0, 100)}...]`;
        }
        scrollToBottom();
      } else if (data.type === "error") {
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = data.content;
        lastMsg.loading = false;
        lastMsg.error = true;
      }
    },
    onDone: () => {
      const lastMsg = agentStore.messages[agentStore.messages.length - 1];
      if (lastMsg.loading) {
        lastMsg.loading = false;
      }
      agentStore.setLoading(false);
    },
    onError: (err) => {
      const lastMsg = agentStore.messages[agentStore.messages.length - 1];
      lastMsg.content = `抱歉，处理出错了：${err.message}`;
      lastMsg.loading = false;
      lastMsg.error = true;
      agentStore.setLoading(false);
      ElMessage.error("对话请求失败，请重试");
    },
  });

  // 保存 中断函数到 store
  agentStore.abortController = stop;
}

/** 停止生成 */
function handleStop() {
  agentStore.abort();
  const lastMsg = agentStore.messages[agentStore.messages.length - 1];
  if (lastMsg.loading) {
    lastMsg.loading = false;
    lastMsg.content += "\n[已停止生成]";
  }
}

/** 触发文件选择框 */
function triggerFileInput() {
  fileInputRef.value?.click();
}

/** 文件选择回调 */
function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) {
    selectedFile.value = file;
    // 临时保存文件路径（后续上传用）
    file._tempPath = URL.createObjectURL(file);
    ElMessage.info(`${file.name} 已选择`);
  }
}

/** 滚动到底部 */
function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight;
    }
  });
}

/**
 * 快捷单图检测流程：
 * 1. 用户点击"📷 单图检测"按钮
 * 2. 弹出文件选择框
 * 3. 选择图片后，调用 detectSingle API
 * 4. 将结果以"用户消息 + AI 结果卡片"的形式插入对话
 */
async function handleQuickDetect(type) {
  if (type === "single") {
    // 创建隐藏的文件选择器
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      // 添加用户消息（显示文件名）
      agentStore.addMessage({
        role: "user",
        content: `[快捷检测] ${file.name}`,
        image: file.name,
        imagePreview: URL.createObjectURL(file),
      });

      // 添加加载占位
      agentStore.addMessage({
        role: "assistant",
        content: "正在检测中...",
        loading: true,
      });

      // 构造 FormData 并调用 API
      const formData = new FormData();
      formData.append("file", file);

      try {
        const result = await detectSingle(formData);
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = `检测完成！发现 ${result.total_objects} 个目标。`;
        lastMsg.loading = false;
        lastMsg.detectionResult = result;
      } catch (err) {
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = "检测失败，请重试";
        lastMsg.loading = false;
      }
    };
    input.click();
  } else if (type === "batch") {
    // 批量检测（支持多选 + ZIP）
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*,.zip";
    input.multiple = true;
    input.onchange = async (e) => {
      const files = Array.from(e.target.files);
      if (!files.length) return;

      const isZip = files.some((f) => f.name.endsWith(".zip"));
      const formData = new FormData();

      if (isZip && files.length === 1) {
        // 单个 ZIP 文件
        formData.append("file", files[0]);
        agentStore.addMessage({
          role: "user",
          content: `[快捷检测] ZIP: ${files[0].name}`,
        });
      } else {
        // 多张图片
        files.forEach((f) => formData.append("files", f));
        const imagePreviews = files.map((f) => URL.createObjectURL(f));
        agentStore.addMessage({
          role: "user",
          content: `[快捷检测] ${files.length} 张图片`,
          images: imagePreviews,
        });
      }

      agentStore.addMessage({
        role: "assistant",
        content: "正在批量检测中...",
        loading: true,
      });

      try {
        const apiCall = isZip ? detectZip(formData) : detectBatch(formData);
        const result = await apiCall;
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];

        // 检查是否有错误
        if (result.error) {
          lastMsg.content = `批量检测失败：${result.error}`;
          lastMsg.loading = false;
          lastMsg.error = true;
          return;
        }

        const totalObjects = result.total_objects ?? 0;
        lastMsg.content = `批量检测完成！共 ${totalObjects} 个目标。`;
        lastMsg.loading = false;
        lastMsg.detectionResult = result;
        console.log("[批量检测结果]", result);
      } catch (err) {
        console.error("[批量检测异常]", err);
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = `批量检测失败：${err.message || err}`;
        lastMsg.loading = false;
        lastMsg.error = true;
      }
    };
    input.click();
  }
}

onMounted(() => {
  // 页面加载时显示欢迎消息
  if (agentStore.messages.length === 0) {
    agentStore.addMessage({
      role: "assistant",
      content:
        "你好！我是 RSOD 目标检测智能体助手。\n\n你可以：\n- 上传一张图片，让我帮你检测目标\n- 使用下方的快捷按钮直接触发检测\n- 用自然语言描述你的需求\n\n试试发一张图片给我吧！",
    });
  }
});
</script>

<style lang="scss" scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f5f5;
}

/* ── 消息列表 ── */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.message-item {
  display: flex;
  margin-bottom: 16px;

  &.message-user {
    justify-content: flex-end;
  }

  &.message-assistant {
    justify-content: flex-start;
  }
}

.message-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.5;
  word-break: break-word;
}

.user-bubble {
  background: #409eff;
  color: white;
  border-bottom-right-radius: 4px;
}

.assistant-bubble {
  background: white;
  border: 1px solid #e0e0e0;
  border-bottom-left-radius: 4px;
}

.message-content {
  white-space: pre-wrap;
}

.markdown-body {
  /* markdown 渲染后的 HTML 样式 */
  h1,
  h2,
  h3 {
    margin-top: 8px;
    margin-bottom: 4px;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    margin: 8px 0;
  }
  th,
  td {
    border: 1px solid #e0e0e0;
    padding: 4px 8px;
  }
  code {
    background: #f0f0f0;
    padding: 2px 4px;
    border-radius: 3px;
  }
}

.typing-indicator {
  display: flex;
  gap: 4px;

  span {
    width: 6px;
    height: 6px;
    background: #999;
    border-radius: 50%;
    animation: typing 1.2s infinite;
  }

  span:nth-child(2) {
    animation-delay: 0.2s;
  }
  span:nth-child(3) {
    animation-delay: 0.4s;
  }
}

/* ── 快捷操作栏 ── */
.quick-actions {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid #e0e0e0;
  background: white;
}

/* ── 输入区域 ── */
.input-area {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid #e0e0e0;
  background: white;

  .el-input {
    flex: 1;
  }
}

/* ── 附件预览 ── */
.message-attachment {
  margin-top: 8px;

  img {
    max-width: 200px;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
  }
}

/* ── 多图附件网格 ── */
.message-attachments-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 8px;
  margin-top: 8px;

  img {
    width: 100%;
    height: 80px;
    object-fit: cover;
    border-radius: 6px;
    border: 1px solid #e0e0e0;
  }
}

/* ── 工具调用信息 ── */
.tool-call-info {
  margin-top: 8px;
  padding: 4px 8px;
  background: #f5f5f5;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
}

@keyframes typing {
  0%,
  60%,
  100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-4px);
  }
}
</style>
```

### 7.3 检测 API 封装

文件：`frontend/src/api/detection.js`

```javascript
/**
 * 检测相关 API 接口
 *
 * 快捷按钮直接调用这些接口（跳过 LLM），结果渲染在对话中
 */
import request from "@/utils/request";

/**
 * 单图检测
 * @param {FormData} formData - 包含 file 字段的 FormData
 * @returns {Promise} - 检测结果（标注图 + 目标统计）
 */
export function detectSingle(formData) {
  // 不设置 Content-Type，让 axios 自动添加 multipart/form-data + boundary
  return request.post("/detection/single", formData, {
    timeout: 60000,
  });
}

/**
 * 批量检测
 * @param {FormData} formData - 包含多个 files 字段的 FormData
 * @returns {Promise} - 批量检测结果
 */
export function detectBatch(formData) {
  return request.post("/detection/batch", formData, {
    timeout: 120000,
  });
}

/**
 * ZIP 检测
 * @param {FormData} formData - 包含 file 字段的 FormData
 * @returns {Promise} - ZIP 解压后的批量检测结果
 */
export function detectZip(formData) {
  return request.post("/detection/zip", formData, {
    timeout: 180000,
  });
}

/**
 * 获取检测任务状态
 * @param {number} taskId - 检测任务 ID
 * @returns {Promise} - 任务状态和结果
 */
export function getDetectionStatus(taskId) {
  return request.get(`/detection/status/${taskId}`);
}
```

---

## 八、前端检测结果卡片组件

### 8.1 组件设计

检测结果卡片用于在对话中可视化展示检测结果，包含标注图和统计信息。

```
┌────────────────────────────────────────────┐
│  📊 检测结果                                │
├────────────────────────────────────────────┤
│                                            │
│  ┌──────────────────────┐                  │
│  │                      │  检测到 5 个目标  │
│  │   [标注图预览]        │  推理耗时 45ms   │
│  │                      │                  │
│  │  飞机 ██  油罐 ██    │  ┌──────────────┐│
│  └──────────────────────┘  │类别    数量   ││
│                            │──────────────││
│                            │飞机     3     ││
│                            │油罐     2     ││
│                            └──────────────┘│
│                                            │
└────────────────────────────────────────────┘
```

### 8.2 DetectionResultCard.vue 实现

文件：`frontend/src/components/DetectionResultCard.vue`

```vue
<template>
  <div class="detection-result-card">
    <div class="card-header">
      <el-icon><DataAnalysis /></el-icon>
      <span>检测结果</span>
      <el-tag size="small" type="success">
        {{ result.total_objects ?? 0 }} 个目标
      </el-tag>
    </div>

    <div class="card-body">
      <!-- 单图模式：标注图 -->
      <div class="result-image" v-if="annotatedImageSrc && !isBatch">
        <img
          :src="annotatedImageSrc"
          alt="检测标注图"
          @click="showFullImage = true"
        />
      </div>

      <!-- 批量模式：多图展示 -->
      <div class="result-images-grid" v-if="isBatch && batchImages.length > 0">
        <div
          v-for="(img, index) in batchImages"
          :key="index"
          class="grid-image"
          @click="previewImage(img)"
        >
          <img :src="img.src" :alt="img.name" />
          <span class="image-name">{{ img.name }}</span>
        </div>
      </div>

      <!-- 统计信息 -->
      <div class="result-stats">
        <div class="stat-item">
          <span class="stat-label">推理耗时</span>
          <span class="stat-value">{{ result.inference_time || result.total_inference_time || 0 }}ms</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">检测目标</span>
          <span class="stat-value">{{ result.total_objects ?? 0 }} 个</span>
        </div>
        <div class="stat-item" v-if="isBatch">
          <span class="stat-label">图片数量</span>
          <span class="stat-value">{{ result.total_images ?? batchImages.length }} 张</span>
        </div>

        <!-- 类别统计表格 -->
        <el-table
          v-if="classCountsArray.length > 0"
          :data="classCountsArray"
          size="small"
          style="margin-top: 12px"
        >
          <el-table-column prop="className" label="类别" />
          <el-table-column prop="count" label="数量" width="80" />
        </el-table>
      </div>
    </div>

    <!-- 全屏图片预览 -->
    <el-dialog v-model="showFullImage" title="检测标注图" width="80%">
      <img
        v-if="previewSrc"
        :src="previewSrc"
        style="width: 100%"
        alt="检测标注图"
      />
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * DetectionResultCard — 检测结果卡片组件
 *
 * 在对话消息中展示检测结果，包含：
 *   - 标注图预览（单图/批量多图，点击可放大）
 *   - 目标总数和推理耗时
 *   - 各类别数量统计表格
 */
import { DataAnalysis } from "@element-plus/icons-vue";
import { computed, ref } from "vue";

const props = defineProps({
  result: {
    type: Object,
    required: true,
  },
});

const showFullImage = ref(false);
const previewSrc = ref(null);

/** 判断是否为批量检测结果 */
const isBatch = computed(() => {
  return Array.isArray(props.result.annotated_images) && props.result.annotated_images.length > 0;
});

/** 单图模式：标注图 URL（优先使用 MinIO URL，否则用 base64） */
const annotatedImageSrc = computed(() => {
  if (props.result.annotated_image_url) {
    return props.result.annotated_image_url;
  }
  if (props.result.annotated_image_base64) {
    return `data:image/jpeg;base64,${props.result.annotated_image_base64}`;
  }
  return null;
});

/** 批量模式：标注图列表 */
const batchImages = computed(() => {
  if (!isBatch.value) return [];
  return props.result.annotated_images.map((img) => ({
    name: img.image_path || "image",
    src: `data:image/jpeg;base64,${img.annotated_image_base64}`,
  }));
});

/** 点击预览图片 */
function previewImage(img) {
  previewSrc.value = img.src;
  showFullImage.value = true;
}

/** 类别统计转为数组（用于 el-table） */
const classCountsArray = computed(() => {
  const counts = props.result.class_counts || {};
  return Object.entries(counts).map(([className, count]) => ({
    className,
    count,
  }));
});
</script>

<style lang="scss" scoped>
.detection-result-card {
  margin-top: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #e0e0e0;
  font-weight: 600;
  font-size: 14px;
}

.card-body {
  display: flex;
  gap: 16px;
  padding: 12px;
}

.result-image {
  flex: 1;
  min-width: 0;

  img {
    width: 100%;
    max-height: 300px;
    object-fit: contain;
    border-radius: 4px;
    cursor: pointer;
    transition: opacity 0.2s;

    &:hover {
      opacity: 0.8;
    }
  }
}

.result-images-grid {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;

  .grid-image {
    text-align: center;
    cursor: pointer;

    img {
      width: 100%;
      height: 100px;
      object-fit: cover;
      border-radius: 4px;
      border: 1px solid #e0e0e0;
      transition: opacity 0.2s;

      &:hover {
        opacity: 0.8;
      }
    }

    .image-name {
      display: block;
      font-size: 11px;
      color: #909399;
      margin-top: 4px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}

.result-stats {
  flex: 0 0 180px;

  .stat-item {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
    font-size: 13px;
  }

  .stat-label {
    color: #909399;
  }

  .stat-value {
    font-weight: 600;
    color: #303133;
  }
}
</style>
```

---

## 九、快捷操作栏（双通道架构）

### 9.1 双通道架构说明

本平台采用**快捷按钮 + 自然语言**双通道架构，确保不同使用场景下的最佳体验：

```
┌────────────────────────────────────────────────────────────────┐
│                    双通道检测架构                                 │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  通道 1: 快捷按钮（直接调 API）                                  │
│  ┌──────────┐  POST /api/detection/   ┌──────────────────┐    │
│  │  📷 按钮  │ ──────────────────→     │ DetectionService │    │
│  └──────────┘  （不经过 LLM）          │ (YOLO 推理)      │    │
│                                        └────────┬─────────┘    │
│  优势：零延迟，结果确定性高                        ↓            │
│  场景：明确知道要检测什么图片                  ┌──────────┐     │
│                                               │ 结果卡片 │     │
│  通道 2: 自然语言（走 Agent）                  └──────────┘     │
│  ┌──────────┐  "帮我分析这张图"  ┌────────┐                   │
│  │ 输入框   │ ─────────────────→ │ Agent  │ → Tool Call       │
│  └──────────┘                    │ (LLM)  │ → 检测结果        │
│                                   └────────┘                   │
│  优势：自然灵活，支持模糊意图                                       │
│  场景："帮我看看这张图里有什么"、"分析一下"                         │
│                                                                │
│  降级策略：                                                      │
│  - LLM 不可用时，快捷按钮仍然可用                                  │
│  - 平台不会因 LLM 故障而完全瘫痪                                   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 9.2 快捷按钮 API

文件：`backend/app/api/detection.py`（新增快捷检测 API）

```python
"""
检测 API 路由 — 快捷检测接口（跳过 LLM，直接调用 YOLO）

接口列表：
  - POST /api/detection/single     单图检测
  - POST /api/detection/batch      批量检测
  - POST /api/detection/zip        ZIP 文件检测
  - GET  /api/detection/status/:id 查询任务状态
"""

import os
import tempfile

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import JSONResponse

from app.api.auth import get_current_user
from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import DetectionTask
from app.services.detection_service import detection_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/detection", tags=["快捷检测"])


@router.post("/single", summary="单图检测")
async def detect_single_api(
    file: UploadFile = File(..., description="检测图片"),
    conf: float = Form(0.25, description="置信度阈值"),
    scene_id: int = Form(None, description="场景 ID"),
    current_user=Depends(get_current_user),
):
    """
    快捷单图检测（跳过 LLM，直接调用 YOLO）
    """
    suffix = os.path.splitext(file.filename)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = detection_service.detect_single(
            image_path=tmp_path,
            conf=conf,
            scene_id=scene_id,
            user_id=current_user.id,
        )
        result["filename"] = file.filename
        return result
    finally:
        os.unlink(tmp_path)


@router.post("/batch", summary="批量检测")
async def detect_batch_api(
    files: list[UploadFile] = File(..., description="多张图片"),
    conf: float = Form(0.25),
    scene_id: int = Form(None),
    current_user=Depends(get_current_user),
):
    """
    快捷批量检测
    """
    temp_paths = []
    try:
        for file in files:
            suffix = os.path.splitext(file.filename)[1] or ".jpg"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                content = await file.read()
                tmp.write(content)
                temp_paths.append(tmp.name)

        result = detection_service.detect_batch(
            image_paths=temp_paths,
            conf=conf,
            scene_id=scene_id,
            user_id=current_user.id,
        )
        return result
    finally:
        for path in temp_paths:
            try:
                os.unlink(path)
            except Exception:
                pass


@router.post("/zip", summary="ZIP 文件检测")
async def detect_zip_api(
    file: UploadFile = File(..., description="ZIP 压缩包"),
    conf: float = Form(0.25),
    scene_id: int = Form(None),
    current_user=Depends(get_current_user),
):
    """
    快捷 ZIP 检测：解压 ZIP 并批量检测其中所有图片
    """
    suffix = os.path.splitext(file.filename)[1] or ".zip"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = detection_service.detect_zip(
            zip_path=tmp_path,
            conf=conf,
            scene_id=scene_id,
            user_id=current_user.id,
        )
        return result
    finally:
        os.unlink(tmp_path)


@router.get("/status/{task_id}", summary="查询检测任务状态")
async def get_detection_status(
    task_id: int,
    current_user=Depends(get_current_user),
):
    """查询检测任务状态"""
    db = SessionLocal()
    try:
        task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
        if not task:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "任务不存在"},
            )
        return {
            "task_id": task.id,
            "status": task.status,
            "task_type": task.task_type,
            "total_images": task.total_images,
            "total_objects": task.total_objects,
            "completed_at": (
                task.completed_at.isoformat() if task.completed_at else None
            ),
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }
    finally:
        db.close()
```

### 9.3 前端快捷按钮处理逻辑

在 `ChatPage.vue` 中，快捷按钮的处理逻辑（`handleQuickDetect` 函数）会：

1. 触发文件选择对话框
2. 用户选择文件后，直接调用 `/api/detection/single` 或 `/api/detection/batch`
3. 将 API 返回的检测结果渲染为卡片，插入到对话消息中

```javascript
/**
 * 快捷单图检测流程：
 * 1. 用户点击"📷 单图检测"按钮
 * 2. 弹出文件选择框
 * 3. 选择图片后，调用 detectSingle API
 * 4. 将结果以"用户消息 + AI 结果卡片"的形式插入对话
 */
async function handleQuickDetect(type) {
  if (type === "single") {
    // 创建隐藏的文件选择器
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      // 添加用户消息（显示文件名）
      agentStore.addMessage({
        role: "user",
        content: `[快捷检测] ${file.name}`,
        image: file.name,
        imagePreview: URL.createObjectURL(file),
      });

      // 添加加载占位
      agentStore.addMessage({
        role: "assistant",
        content: "正在检测中...",
        loading: true,
      });

      // 构造 FormData 并调用 API
      const formData = new FormData();
      formData.append("file", file);

      try {
        const result = await detectSingle(formData);
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = `检测完成！发现 ${result.total_objects} 个目标。`;
        lastMsg.loading = false;
        lastMsg.detectionResult = result;
      } catch (err) {
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = "检测失败，请重试";
        lastMsg.loading = false;
      }
    };
    input.click();
  } else if (type === "batch") {
    // 批量检测（支持多选 + ZIP）
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*,.zip";
    input.multiple = true;
    input.onchange = async (e) => {
      const files = Array.from(e.target.files);
      if (!files.length) return;

      const isZip = files.some((f) => f.name.endsWith(".zip"));
      const formData = new FormData();

      if (isZip && files.length === 1) {
        // 单个 ZIP 文件
        formData.append("file", files[0]);
        agentStore.addMessage({
          role: "user",
          content: `[快捷检测] ZIP: ${files[0].name}`,
        });
      } else {
        // 多张图片
        files.forEach((f) => formData.append("files", f));
        const imagePreviews = files.map((f) => URL.createObjectURL(f));
        agentStore.addMessage({
          role: "user",
          content: `[快捷检测] ${files.length} 张图片`,
          images: imagePreviews,
        });
      }

      agentStore.addMessage({
        role: "assistant",
        content: "正在批量检测中...",
        loading: true,
      });

      try {
        const apiCall = isZip ? detectZip(formData) : detectBatch(formData);
        const result = await apiCall;
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];

        // 检查是否有错误
        if (result.error) {
          lastMsg.content = `批量检测失败：${result.error}`;
          lastMsg.loading = false;
          lastMsg.error = true;
          return;
        }

        const totalObjects = result.total_objects ?? 0;
        lastMsg.content = `批量检测完成！共 ${totalObjects} 个目标。`;
        lastMsg.loading = false;
        lastMsg.detectionResult = result;
        console.log("[批量检测结果]", result);
      } catch (err) {
        console.error("[批量检测异常]", err);
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = `批量检测失败：${err.message || err}`;
        lastMsg.loading = false;
        lastMsg.error = true;
      }
    };
    input.click();
  }
}
```

---

### 9.4 优化frontend/src/utils/stream.js 文件

```js
/**
 * SSE (Server-Sent Events) 流式处理工具
 * 用于 Day 11 智能体对话的流式渲染
 *
 * 使用方式：
 *   const stop = streamChat(
 *     '/api/chat/stream',
 *     { message: '你好' },
 *     {
 *       onMessage: (chunk) => { content += chunk },
 *       onDone: () => { console.log('完成') },
 *       onError: (err) => { console.error(err) },
 *     }
 *   )
 */

/**
 * 发起 SSE 流式请求
 *
 * @param {string} url - 请求地址（相对路径，会经过 Vite proxy）
 * @param {Object} body - 请求体
 * @param {Object} callbacks - 回调函数
 * @param {Function} callbacks.onMessage - 收到消息片段时的回调
 * @param {Function} callbacks.onDone - 流结束时的回调
 * @param {Function} callbacks.onError - 错误时的回调
 * @returns {Function} stop - 调用此函数可中断连接
 */
export function streamChat(url, body, callbacks) {
  const { onMessage, onDone, onError } = callbacks;

  // 从 localStorage 获取 Token
  const token = localStorage.getItem("rsod_token");

  // 使用 fetch + ReadableStream 实现 SSE
  const controller = new AbortController();

  fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      // 缓冲区：用于拼接跨 chunk 的不完整 SSE 消息
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          // 流结束，处理缓冲区剩余数据
          if (buffer.trim()) {
            processSSEMessage(buffer, onMessage);
          }
          onDone?.();
          break;
        }

        // 解码并追加到缓冲区
        buffer += decoder.decode(value, { stream: true });

        // 按双换行分割完整的 SSE 消息
        const messages = buffer.split("\n\n");

        // 最后一个元素可能是不完整的，保留在缓冲区
        buffer = messages.pop() || "";

        // 处理完整的消息
        for (const msg of messages) {
          if (msg.trim()) {
            const shouldStop = processSSEMessage(msg, onMessage);
            if (shouldStop) {
              onDone?.();
              return;
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError?.(err);
      }
    });

  // 返回中断函数
  return () => controller.abort();
}

/**
 * 处理单条 SSE 消息
 * @param {string} message - 完整的 SSE 消息（可能包含多行 data:）
 * @param {Function} onMessage - 消息回调
 * @returns {boolean} 是否应该停止（遇到 [DONE]）
 */
function processSSEMessage(message, onMessage) {
  // SSE 消息可能包含多行（data:, event:, id: 等），只处理 data: 行
  const lines = message.split("\n");

  for (const line of lines) {
    if (line.startsWith("data: ")) {
      const data = line.slice(6); // 去掉 "data: " 前缀

      if (data === "[DONE]") {
        return true;
      }

      try {
        const parsed = JSON.parse(data);
        onMessage?.(parsed);
      } catch {
        // JSON 解析失败，可能是数据太大或被截断
        // 尝试作为纯文本处理
        console.warn("[SSE] JSON解析失败，数据长度:", data.length);
        onMessage?.({ type: "text_chunk", content: data });
      }
    }
  }

  return false;
}
```

注意：添加缓冲区，按 SSE 协议（双换行 \n\n ）正确分割消息。

## 十、前后端联调测试

### 10.1 联调测试流程

```
┌────────────────────────────────────────────────────────────────┐
│                    Day 8 联调测试流程                             │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  测试 1: 自然语言触发单图检测                                     │
│  ┌──────────┐  "检测这张图片"   ┌────────┐  Tool Call           │
│  │ 前端     │ ──────────────→  │ Agent  │ ────────→ 检测       │
│  │ ChatPage │  ←─── SSE ────  │        │ ←── 结果返回          │
│  └──────────┘  结果卡片         └────────┘                     │
│                                                                │
│  测试 2: 快捷按钮单图检测                                        │
│  ┌──────────┐  点击"📷单图"   ┌──────────────────┐            │
│  │ 前端     │ ─────────────→  │ /api/detection/  │            │
│  │ ChatPage │  ←── JSON ───  │ single           │            │
│  └──────────┘  结果卡片         └──────────────────┘            │
│                                                                │
│  测试 3: 快捷按钮批量/ZIP 检测                                   │
│  ┌──────────┐  选择 ZIP 文件  ┌──────────────────┐            │
│  │ 前端     │ ─────────────→  │ /api/detection/  │            │
│  │ ChatPage │  ←── JSON ───  │ zip              │            │
│  └──────────┘  结果卡片         └──────────────────┘            │
│                                                                │
│  测试 4: 中断对话                                                │
│  ┌──────────┐  点击"停止"     ┌──────────────────┐            │
│  │ 前端     │ ── AbortCtrl ─→ │ SSE 连接断开     │            │
│  └──────────┘                  └──────────────────┘            │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 10.2 测试 Checklist

**后端测试**：

```bash
# 1. 启动后端服务
cd backend
python main.py

# 2. 测试 SSE 对话接口（无图片）
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message":"你好"}'

# 3. 测试快捷单图检测
curl -X POST http://localhost:8000/api/detection/single \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.jpg" \
  -F "conf=0.25"

# 4. 测试 ZIP 检测
curl -X POST http://localhost:8000/api/detection/zip \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@images.zip" \
  -F "conf=0.25"
```

**前端测试**：

```bash
# 启动前端开发服务器
cd frontend
npm run dev
```

1. 打开 http://localhost:5173/chat
2. 确认看到欢迎消息
3. 输入"你好" → 观察 SSE 流式响应
4. 点击"📷 单图检测" → 选择图片 → 观察结果卡片
5. 点击"📁 批量/ZIP" → 选择 ZIP → 观察批量结果
6. 输入"检测这张图片"并附带图片 → 观察 Agent Tool Calling 过程
7. 点击"停止"按钮 → 确认流式请求被中断

---

## 十一、Day 8 里程碑验收

### 11.1 验收流程

| 步骤 | 验收项 | 达标标准 | 权重 |
| ---- | ------ | -------- | ---- |
| 1 | DetectionService 单图检测 | 上传任意图片，返回标注图 + 统计 | 20% |
| 2 | DetectionService 批量检测 | 上传 ≥ 3 张图片，返回汇总结果 | 15% |
| 3 | DetectionService ZIP 检测 | 上传 ZIP 包，自动解压 + 检测 | 15% |
| 4 | SSE 流式对话 | 文字逐字显示，无卡顿 | 15% |
| 5 | Agent Tool Calling | 自然语言触发检测，Agent 正确调用工具 | 15% |
| 6 | 快捷按钮检测 | 点击按钮即触发，零延迟 | 10% |
| 7 | 检测结果卡片 | 标注图 + 统计表格完整展示 | 10% |

### 11.2 评分标准

| 等级 | 分数范围 | 标准 |
| ---- | -------- | ---- |
| 优秀 | 90-100 | 全部功能完成，代码规范，额外优化 |
| 良好 | 75-89 | 核心功能完成，有少量 Bug |
| 合格 | 60-74 | 基本功能可用，存在明显问题 |
| 不合格 | < 60 | 核心功能未完成 |

---

## 十二、常见问题排查

| 问题 | 原因 | 解决方案 |
| ---- | ---- | -------- |
| Agent 初始化报错 `ModuleNotFoundError` | 未安装 langchain 相关包 | `pip install langchain langchain-openai langchain-community` |
| SSE 流式请求无数据返回 | Vite proxy 未正确转发 | 检查 `vite.config.js` 中的 proxy 配置 |
| LLM 调用超时 | API Key 无效或网络问题 | 检查 `.env` 中的 API Key，确认网络可达 |
| 检测结果卡片不显示 | Agent 未返回检测结果 | 检查后端日志，确认 Tool 是否被正确调用 |
| 快捷按钮检测报错 404 | 未注册 detection 路由 | 在 `main.py` 中添加 `app.include_router(detection_router)` |
| `yolo11n.pt` 下载失败 | 网络问题（Ultralytics 需从 GitHub 下载） | 手动下载 `yolo11n.pt` 放到项目根目录 |
| ZIP 解压失败 | ZIP 文件损坏或格式不对 | 确认 ZIP 文件可用标准解压工具打开 |
| 标注图显示为空白 | base64 编码截断 | 检查 `cv2.imencode` 的 JPEG 质量参数 |
| 前端文件上传后无法检测 | 文件路径未正确传递 | 检查 `FormData` 中的 `file` 字段名是否与后端一致 |
| Agent 循环次数超限 | LLM 反复调用工具无结果 | 设置 `max_iterations=5` 限制，优化 system prompt |

---

## 十三、Day 8 验收自查清单

### 后端

- [ ] `backend/app/agent/__init__.py` 文件存在
- [ ] `backend/app/agent/detection_agent.py` 包含 ReAct Agent + 3 个检测 Tool
- [ ] `backend/app/services/detection_service.py` 包含 detect_single / detect_batch / detect_zip
- [ ] `backend/app/api/chat.py` 包含 `/api/chat/stream` SSE 接口
- [ ] `backend/app/api/chat.py` 包含 `/api/detection/single`、`/api/detection/batch`、`/api/detection/zip` 快捷接口
- [ ] `backend/main.py` 已注册 chat_router
- [ ] `.env` 中已配置 LLM API Key（QWEN_API_KEY 或 OPENAI_API_KEY）
- [ ] `requirements.txt` 包含 langchain、langchain-openai 依赖

### 前端

- [ ] `frontend/src/views/ChatPage.vue` 完整实现（消息气泡 + 文件上传 + 流式渲染）
- [ ] `frontend/src/components/DetectionResultCard.vue` 完整实现（标注图 + 统计表格）
- [ ] `frontend/src/api/detection.js` 封装了 detectSingle / detectBatch / detectZip
- [ ] 快捷操作栏包含单图检测和批量/ZIP 检测按钮
- [ ] 发送按钮和停止按钮可正确切换
- [ ] 消息列表自动滚动到底部

### 功能验证

- [ ] 输入"你好" → AI 流式回复（逐字显示）
- [ ] 点击"📷 单图检测" → 选择图片 → 结果卡片展示（标注图 + 统计）
- [ ] 点击"📁 批量/ZIP" → 选择 ZIP → 批量结果展示
- [ ] 输入"检测这张图片"并附图 → Agent 调用 detect_single_image → 结果卡片
- [ ] 点击"停止"按钮 → 流式请求中断
- [ ] 快捷按钮在 LLM 不可用时仍可使用（降级策略）

---

> **Day 8 总结**：今天我们从零搭建了智能对话系统的核心骨架——LangChain Agent + 检测 Service + SSE 流式通信 + 对话 UI。这是整个平台从"工具"升级为"智能体"的关键一步。在 Day 9 中，我们将在此基础上继续扩展视频检测和摄像头实时检测功能。