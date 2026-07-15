"""
知识库管理 API 路由
- POST   /api/knowledge/upload            上传文档（PDF/TXT/MD）
- GET    /api/knowledge/documents          获取知识文档列表
- DELETE /api/knowledge/documents/{id}     删除知识文档
- POST   /api/knowledge/search            测试检索（调试用）
"""

import os

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
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
    title: Optional[str] = Form(None, description="文档标题，不传则使用文件名"),
    source_type: str = Form("upload", description="来源类型：upload（用户上传）/ preset（系统预置）"),
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
# 批量构建预置文档索引
# ══════════════════════════════════════════════════════════════


@router.post("/build")
async def build_preset_documents(
    current_user=Depends(get_current_user),
):
    """
    批量构建预置知识文档索引

    扫描 backend/knowledge_base/ 目录下的所有 .md/.txt/.pdf 文件，
    逐个解析、切片、向量化入库。跳过已入库的同名文档。
    """
    kb_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "knowledge_base")

    if not os.path.isdir(kb_dir):
        raise HTTPException(status_code=404, detail=f"知识库目录不存在: {kb_dir}")

    # 扫描支持的文件
    supported_ext = (".md", ".txt", ".pdf")
    files = [
        f for f in os.listdir(kb_dir)
        if os.path.splitext(f)[1].lower() in supported_ext
    ]

    if not files:
        raise HTTPException(status_code=404, detail="知识库目录中没有找到支持的文件")

    # 获取已有文档列表，避免重复入库
    existing_docs = rag_service.list_documents()
    existing_titles = {doc["title"] for doc in existing_docs}

    results = []
    skipped = 0
    for filename in files:
        title = os.path.splitext(filename)[0]
        if title in existing_titles:
            results.append({"file": filename, "status": "skipped", "reason": "已存在"})
            skipped += 1
            continue

        file_path = os.path.join(kb_dir, filename)
        result = rag_service.ingest_document(
            file_path=file_path,
            title=title,
            source_type="preset",
            uploaded_by=current_user["id"],
        )

        if "error" in result:
            results.append({"file": filename, "status": "error", "error": result["error"]})
        else:
            results.append({
                "file": filename,
                "status": "success",
                "chunk_count": result["chunk_count"],
            })

    logger.info(
        "批量构建知识库完成: 总计 %d 个文件，成功 %d，跳过 %d",
        len(files),
        len(files) - skipped - sum(1 for r in results if r["status"] == "error"),
        skipped,
    )

    return {
        "message": f"构建完成：共 {len(files)} 个文件，成功 {len(files) - skipped}，跳过 {skipped}",
        "details": results,
    }


# ══════════════════════════════════════════════════════════════
# 统计信息
# ══════════════════════════════════════════════════════════════


@router.get("/stats")
async def get_stats(current_user=Depends(get_current_user)):
    """
    获取知识库统计信息

    返回文档数量、总片段数等统计数据。
    """
    from app.database.session import SessionLocal
    from app.entity.db_models import KnowledgeChunk, KnowledgeDocument
    from sqlalchemy import func

    db = SessionLocal()
    try:
        doc_count = db.query(KnowledgeDocument).count()
        chunk_count = db.query(func.count(KnowledgeChunk.id)).scalar() or 0
        preset_count = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.source_type == "preset"
        ).count()
        upload_count = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.source_type == "upload"
        ).count()

        return {
            "document_count": doc_count,
            "chunk_count": chunk_count,
            "preset_count": preset_count,
            "upload_count": upload_count,
        }
    finally:
        db.close()


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
