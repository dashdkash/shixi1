"""
RAG 核心服务 — 文档入库 + 向量检索

职责：
  - 文档解析（PDF / TXT / MD）
  - 文本切片（RecursiveCharacterTextSplitter）
  - 向量化 + 入库（Embedding + pgvector）
  - 余弦相似度检索（cosine_distance）
  - 文档管理（列表 / 删除）

使用方式：
  from app.services.rag_service import rag_service

  doc = rag_service.ingest_document("path/to/file.pdf", "标题")
  results = rag_service.search("YOLO 如何使用？", top_k=5)
"""

import os
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import SessionLocal, get_psycopg2_conn
from app.entity.db_models import KnowledgeChunk, KnowledgeDocument
from app.services.embedding_service import embedding_service
from app.services.reranker_service import reranker_service

logger = get_logger(__name__)


class RAGService:
    """RAG 知识库服务"""

    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.RAG_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "！", "？", ".", " "],
        )

    # ── 文档解析 ─────────────────────────────────────────

    @staticmethod
    def _parse_file(file_path: str, file_type: str) -> str:
        """
        解析文件为纯文本

        支持 PDF / TXT / MD
        """
        if file_type == "pdf":
            from pypdf import PdfReader

            reader = PdfReader(file_path)
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n\n".join(pages)
        else:
            # TXT / MD 直接读取
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

    # ── 文档入库 ─────────────────────────────────────────

    def ingest_document(
        self,
        file_path: str,
        title: str,
        source_type: str = "upload",
        uploaded_by: Optional[int] = None,
    ) -> dict:
        """
        解析文档 → 切片 → 向量化 → 存入数据库

        Args:
            file_path: 文件路径
            title: 文档标题
            source_type: 来源类型 "upload" / "preset"
            uploaded_by: 上传人 user_id

        Returns:
            {"id": int, "title": str, "chunk_count": int}
        """
        db = SessionLocal()
        try:
            # 1. 解析文件
            ext = os.path.splitext(file_path)[1].lower().lstrip(".")
            if ext not in ("pdf", "txt", "md"):
                return {"error": f"不支持的文件类型: {ext}"}

            raw_text = self._parse_file(file_path, ext)
            if not raw_text.strip():
                return {"error": "文件内容为空"}

            # 2. 文本切片
            chunks = self.splitter.split_text(raw_text)
            logger.info("文档切片完成: %s → %d 个片段", title, len(chunks))

            # 3. 批量向量化
            embeddings = embedding_service.embed_texts(chunks)

            # 4. 创建文档记录
            doc = KnowledgeDocument(
                title=title,
                file_type=ext,
                file_path=file_path,
                chunk_count=len(chunks),
                source_type=source_type,
                uploaded_by=uploaded_by,
            )
            db.add(doc)
            db.flush()

            # 5. 批量插入片段
            for i, (text, vector) in enumerate(zip(chunks, embeddings)):
                chunk = KnowledgeChunk(
                    document_id=doc.id,
                    content=text,
                    metadata_={"chunk_index": i, "title": title},
                    embedding=vector,
                )
                db.add(chunk)

            db.commit()
            db.refresh(doc)

            logger.info(
                "文档入库成功: id=%d, title=%s, chunks=%d",
                doc.id, doc.title, doc.chunk_count,
            )

            return {
                "id": doc.id,
                "title": doc.title,
                "chunk_count": doc.chunk_count,
                "source_type": doc.source_type,
                "created_at": doc.created_at.isoformat(),
            }

        except Exception as e:
            db.rollback()
            logger.error("文档入库失败: %s", str(e), exc_info=True)
            return {"error": f"文档入库失败: {str(e)}"}
        finally:
            db.close()

    # ── 向量检索 ─────────────────────────────────────────

    def search(self, query: str, top_k: int = None) -> list[dict]:
        """
        语义检索知识库

        将查询文本向量化后，在 pgvector 中做余弦相似度搜索。

        Args:
            query: 查询文本
            top_k: 返回结果数量，默认使用配置

        Returns:
            检索结果列表:
            [{"content": str, "score": float, "title": str, "metadata": dict}, ...]
        """
        if top_k is None:
            top_k = settings.RAG_TOP_K

        # 使用 psycopg2 原生连接，避免 SQLAlchemy :param 与 PG ::vector 语法冲突
        conn = get_psycopg2_conn()
        try:
            # 1. 查询向量化
            query_vector = embedding_service.embed_query(query)
            vector_str = "[" + ",".join(str(x) for x in query_vector) + "]"

            # 2. 使用 pgvector <=> 算子做余弦距离检索（psycopg2 原生 SQL）
            sql = """
                SELECT
                    kc.id,
                    kc.content,
                    kc.metadata,
                    kc.document_id,
                    kd.title AS doc_title,
                    (kc.embedding <=> %s::vector) AS distance
                FROM knowledge_chunks kc
                JOIN knowledge_documents kd ON kd.id = kc.document_id
                ORDER BY kc.embedding <=> %s::vector
                LIMIT %s
            """

            cursor = conn.cursor()
            cursor.execute(sql, (vector_str, vector_str, top_k))
            rows = cursor.fetchall()

            # 3. 组装结果
            search_results = []
            for row in rows:
                distance = float(row[5])  # distance 列在第6位
                score = 1.0 - distance  # distance 0~2 → score 1~-1

                search_results.append({
                    "content": row[1],
                    "score": round(score, 4),
                    "title": row[4] or "未知",
                    "document_id": row[3],
                    "metadata": row[2] or {},
                })

            logger.info(
                "知识库检索: query=%s, top_k=%d, 命中 %d 条",
                query[:50], top_k, len(search_results),
            )

            # 4. Reranker 重排
            if settings.RAG_ENABLE_RERANK and search_results:
                search_results = reranker_service.rerank(query, search_results)

            return search_results

        except Exception as e:
            logger.error("知识库检索失败: %s", str(e), exc_info=True)
            return []
        finally:
            conn.close()

    # ── 文档管理 ─────────────────────────────────────────

    def list_documents(self, user_id=None, is_superuser=False) -> list[dict]:
        """
        列出知识文档，支持可见性过滤

        Args:
            user_id: 当前用户 ID
            is_superuser: 是否为管理员

        管理员可见所有文档，普通用户可见预置文档 + 自己上传的文档。
        """
        db = SessionLocal()
        try:
            query = db.query(KnowledgeDocument)
            if not is_superuser:
                query = query.filter(
                    (KnowledgeDocument.source_type == "preset")
                    | (KnowledgeDocument.uploaded_by == user_id)
                )
            docs = query.order_by(KnowledgeDocument.created_at.desc()).all()
            return [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "file_type": doc.file_type,
                    "chunk_count": doc.chunk_count,
                    "source_type": doc.source_type,
                    "uploaded_by": doc.uploaded_by,
                    "is_owner": doc.uploaded_by == user_id if user_id else False,
                    "created_at": doc.created_at.isoformat(),
                }
                for doc in docs
            ]
        finally:
            db.close()

    def delete_document(self, doc_id: int, user_id=None, is_superuser=False) -> dict:
        """
        删除文档及其所有片段（级联删除）

        Args:
            doc_id: 文档 ID
            user_id: 当前用户 ID
            is_superuser: 是否为管理员

        Returns:
            {"message": str} 或 {"error": str}
        """
        db = SessionLocal()
        try:
            doc = db.query(KnowledgeDocument).filter(
                KnowledgeDocument.id == doc_id
            ).first()

            if not doc:
                return {"error": "文档不存在"}

            # 权限校验：普通用户只能删除自己上传的文档
            if not is_superuser and doc.uploaded_by != user_id:
                return {"error": "无权删除此文档"}

            title = doc.title
            db.delete(doc)
            db.commit()

            logger.info("删除知识文档: id=%d, title=%s", doc_id, title)
            return {"message": f"文档 '{title}' 已删除"}

        except Exception as e:
            db.rollback()
            logger.error("删除文档失败: %s", str(e), exc_info=True)
            return {"error": f"删除失败: {str(e)}"}
        finally:
            db.close()


# 全局单例
rag_service = RAGService()
