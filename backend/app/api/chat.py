"""
智能对话 API 路由
- POST /api/chat/stream  流式对话接口
"""

import json
import time
from typing import Dict, Generator

from app.core.security import decode_access_token
from app.database.session import get_db
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import StreamingResponse
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/chat", tags=["智能对话"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """从 JWT Token 中解析当前用户"""
    credentials_exception = HTTPException(
        status_code=401,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
    except (JWTError, ValueError):
        raise credentials_exception
    return {"id": int(user_id_str)}


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    stream: bool = True


def generate_chat_response(message: str, lang: str) -> Generator[str, None, None]:
    """
    生成流式聊天响应
    根据语言参数返回对应语言的内容
    
    Args:
        message: 用户消息
        lang: 语言标识 (zh/en)
    """
    welcome_responses = {
        "zh": [
            "你好！我是杂草识别智能体。",
            "我可以帮助你识别杂草、分析检测结果。",
            "请问你有什么需要帮助的吗？",
        ],
        "en": [
            "Hello! I am the Weed Detection Agent.",
            "I can help you identify weeds and analyze detection results.",
            "How can I assist you today?",
        ],
    }

    other_responses = {
        "zh": [
            "收到你的消息。",
            "我来帮你分析一下。",
            "请稍等...",
        ],
        "en": [
            "Received your message.",
            "Let me analyze that for you.",
            "Please wait...",
        ],
    }

    if message.lower() in ["hello", "hi", "你好", "嗨", ""]:
        selected_responses = welcome_responses.get(lang, welcome_responses["zh"])
    else:
        selected_responses = other_responses.get(lang, other_responses["zh"])
    
    for response in selected_responses:
        for char in response:
            yield json.dumps({"content": char}) + "\n"
            time.sleep(0.05)
        yield json.dumps({"content": " "}) + "\n"
        time.sleep(0.1)
    
    yield "[DONE]\n"


async def get_current_user_optional(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """可选的用户认证，允许未认证访问"""
    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if user_id_str is not None:
            return {"id": int(user_id_str)}
    except (JWTError, ValueError):
        pass
    return None


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    accept_language: str = Header(None),
    current_user=Depends(get_current_user_optional),
):
    """
    流式对话接口
    
    - 根据 Accept-Language 请求头决定响应语言
    - 返回 SSE 格式的流式响应
    - 支持未认证访问（用于欢迎消息）
    
    Args:
        request: 聊天请求
        accept_language: 语言偏好 (zh-CN, zh, en-US, en)
    """
    lang = "zh"
    if accept_language:
        if "en" in accept_language.lower():
            lang = "en"
        elif "zh" in accept_language.lower():
            lang = "zh"
    
    def stream():
        for chunk in generate_chat_response(request.message, lang):
            yield f"data: {chunk}"
    
    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/")
async def chat(
    request: ChatRequest,
    accept_language: str = Header(None),
    current_user=Depends(get_current_user),
):
    """
    非流式对话接口
    
    Args:
        request: 聊天请求
        accept_language: 语言偏好
    """
    lang = "zh"
    if accept_language:
        if "en" in accept_language.lower():
            lang = "en"
        elif "zh" in accept_language.lower():
            lang = "zh"
    
    responses = {
        "zh": "你好！我是杂草识别智能体。我可以帮助你识别杂草、分析检测结果。请问你有什么需要帮助的吗？",
        "en": "Hello! I am the Weed Detection Agent. I can help you identify weeds and analyze detection results. How can I assist you today?",
    }
    
    return {
        "content": responses.get(lang, responses["zh"]),
        "language": lang,
    }
