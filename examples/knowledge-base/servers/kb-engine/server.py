"""知识库检索 MCP 服务器（基于 FastMCP + 简单向量检索）"""
from fastmcp import FastMCP
import json
import hashlib
from pathlib import Path
from typing import Optional

mcp = FastMCP("kb-engine")

# 简单的内存知识库（生产环境应替换为 Chroma/FAISS/Pinecone）
_knowledge_base = {}

def _simple_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]

def _simple_tokenize(text: str) -> list:
    """简单分词（按空格和标点）"""
    return text.lower().replace(".", " ").replace(",", " ").split()

def _simple_similarity(query: str, text: str) -> float:
    """简单的词频相似度（生产环境应用嵌入模型）"""
    query_tokens = set(_simple_tokenize(query))
    text_tokens = set(_simple_tokenize(text))
    if not query_tokens or not text_tokens:
        return 0.0
    intersection = query_tokens & text_tokens
    return len(intersection) / len(query_tokens)

@mcp.tool()
def add_document(file_path: str, chunk_size: int = 512, chunk_overlap: int = 50) -> dict:
    """将文档分块并存入知识库"""
    path = Path(file_path)
    if not path.exists():
        return {"error": f"文件不存在: {file_path}"}
    content = path.read_text(encoding="utf-8", errors="ignore")
    chunks = []
    start = 0
    while start < len(content):
        end = min(start + chunk_size, len(content))
        chunk = content[start:end]
        chunk_id = _simple_hash(chunk)
        _knowledge_base[chunk_id] = {
            "id": chunk_id,
            "source": path.name,
            "content": chunk,
            "chunk_index": len(chunks)
        }
        chunks.append(chunk_id)
        start += chunk_size - chunk_overlap
    return {"document": path.name, "chunks": len(chunks), "total_in_kb": len(_knowledge_base)}

@mcp.tool()
def list_documents() -> dict:
    """列出知识库中所有文档"""
    sources = {}
    for chunk in _knowledge_base.values():
        src = chunk["source"]
        if src not in sources:
            sources[src] = 0
        sources[src] += 1
    return {"documents": [{"name": k, "chunks": v} for k, v in sources.items()], "total_chunks": len(_knowledge_base)}

@mcp.tool()
def delete_document(document_name: str) -> dict:
    """从知识库删除指定文档的所有块"""
    before = len(_knowledge_base)
    to_delete = [k for k, v in _knowledge_base.items() if v["source"] == document_name]
    for k in to_delete:
        del _knowledge_base[k]
    return {"deleted": len(to_delete), "remaining": len(_knowledge_base)}

@mcp.tool()
def search(query: str, top_k: int = 5, score_threshold: float = 0.0) -> dict:
    """语义检索：返回最相关的文档片段"""
    results = []
    for chunk in _knowledge_base.values():
        score = _simple_similarity(query, chunk["content"])
        if score >= score_threshold:
            results.append({
                "id": chunk["id"],
                "source": chunk["source"],
                "chunk_index": chunk["chunk_index"],
                "score": round(score, 4),
                "content": chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"]
            })
    results.sort(key=lambda x: x["score"], reverse=True)
    return {"query": query, "results": results[:top_k], "total": len(results)}

@mcp.tool()
def get_chunk(chunk_id: str) -> dict:
    """获取完整的文档片段内容"""
    if chunk_id not in _knowledge_base:
        return {"error": f"片段不存在: {chunk_id}"}
    chunk = _knowledge_base[chunk_id]
    return {"id": chunk["id"], "source": chunk["source"], "content": chunk["content"]}

if __name__ == "__main__":
    mcp.run()
