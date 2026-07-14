"""
知识库管理 API 路由
- POST   /api/knowledge/upload            上传文档（PDF/TXT/MD）
- GET    /api/knowledge/documents          获取知识文档列表
- DELETE /api/knowledge/documents/{id}     删除知识文档
- POST   /api/knowledge/search            测试检索（调试用）
"""

import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from app.core.logger import get_logger
from app.core.security import decode_access_token
from app.services.rag_service import rag_service
from jose import JWTError

logger = get_logger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["知识库管理"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
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


class SearchRequest(BaseModel):
    """检索请求"""
    query: str
    top_k: int = 5


# ══════════════════════════════════════════════════════════════
# 文档管理
# ══════════════════════════════════════════════════════════════


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(..., description="知识文档文件（PDF/TXT/MD）"),
    title: str = None,
    source_type: str = "upload",
    current_user=Depends(get_current_user),
):
    """
    上传知识文档

    支持 PDF、TXT、MD 格式。上传后自动解析、切片、向量化入库。
    """
    # 校验文件类型
    filename = file.filename or "document.txt"
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if ext not in ("pdf", "txt", "md"):
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}，仅支持 PDF/TXT/MD")

    # 保存文件
    upload_dir = os.path.join(os.getcwd(), "uploads", "knowledge")
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, f"{os.urandom(8).hex()}.{ext}")

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    # 入库
    doc_title = title or os.path.splitext(filename)[0]
    result = rag_service.ingest_document(
        file_path=save_path,
        title=doc_title,
        source_type=source_type,
        uploaded_by=current_user["id"],
    )

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    logger.info(
        "文档上传成功: title=%s, chunks=%d, user=%d",
        doc_title, result["chunk_count"], current_user["id"],
    )

    return result


@router.get("/documents")
async def list_documents(current_user=Depends(get_current_user)):
    """
    获取所有知识文档列表
    """
    return {"data": rag_service.list_documents()}


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    current_user=Depends(get_current_user),
):
    """
    删除知识文档及其所有向量片段
    """
    result = rag_service.delete_document(doc_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ══════════════════════════════════════════════════════════════
# 检索测试
# ══════════════════════════════════════════════════════════════


@router.post("/search")
async def search_knowledge(
    request: SearchRequest,
    current_user=Depends(get_current_user),
):
    """
    测试知识库检索（调试用）

    输入查询文本，返回最相似的知识片段。
    """
    results = rag_service.search(request.query, top_k=request.top_k)
    return {"query": request.query, "results": results}
