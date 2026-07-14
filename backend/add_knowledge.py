r"""
知识库初始化脚本 — 将 shixi1 目录下的 MD 文件导入知识库

用法：必须指定文件名才能导入
  cd backend
  .venv\Scripts\python add_knowledge.py "README.md"
  .venv\Scripts\python add_knowledge.py "7. Day05-xxx.md" "8. Day06-xxx.md"
"""

import os
import sys

# 项目根目录（shixi1）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_md_files(directory: str) -> list[str]:
    """查找目录下所有 .md 文件"""
    return sorted(
        f for f in os.listdir(directory) if f.endswith(".md")
    )


def main():
    if len(sys.argv) < 2:
        # 没有传参 → 列出可用文件并提示用法
        md_files = find_md_files(PROJECT_ROOT)
        print("用法: python add_knowledge.py <文件名> [文件名...]\n")
        if md_files:
            print(f"shixi1 目录下可用的 MD 文件：")
            for f in md_files:
                print(f"  - {f}")
        else:
            print("shixi1 目录下没有找到 .md 文件。")
        return

    files = sys.argv[1:]

    print(f"\n准备导入 {len(files)} 个文件...\n")

    # 导入 RAG 服务（必须在 backend 目录下运行）
    from app.services.rag_service import rag_service

    success_count = 0
    for fname in files:
        file_path = os.path.join(PROJECT_ROOT, fname)

        if not os.path.exists(file_path):
            print(f"  [跳过] 文件不存在: {fname}")
            continue

        title = os.path.splitext(fname)[0]

        print(f"  [导入中] {fname} ...", end=" ")

        result = rag_service.ingest_document(
            file_path=file_path,
            title=title,
            source_type="preset",
            uploaded_by=None,
        )

        if "error" in result:
            print(f"失败 - {result['error']}")
        else:
            print(f"成功 - {result['chunk_count']} 个片段")
            success_count += 1

    print(f"\n导入完成: {success_count}/{len(files)} 个文件成功入库。")


if __name__ == "__main__":
    main()
