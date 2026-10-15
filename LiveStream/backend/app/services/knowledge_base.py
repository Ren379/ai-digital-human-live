###############################################################################
#  Knowledge Base — LangChain Chroma RAG
###############################################################################

import os
from typing import List
from openai import OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from app.utils.logger import logger


class OpenAICompatEmbeddings(Embeddings):
    """最小的 OpenAI 兼容 Embedding 实现。

    不用 langchain_openai.OpenAIEmbeddings，因为它内部的
    _get_len_safe_embeddings 在 DashScope 上会触发参数格式不兼容。
    """

    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        resp = self.client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in sorted(resp.data, key=lambda x: x.index)]

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


class KnowledgeBase:
    """基于 Chroma 的本地知识库，文档加载 + 向量检索"""

    def __init__(
        self,
        docs_path: str,
        persist_path: str,
        embedding_model: str,
        api_key: str,
        base_url: str,
    ):
        self.docs_path = docs_path
        self.persist_path = persist_path
        self.embeddings = OpenAICompatEmbeddings(
            model=embedding_model,
            api_key=api_key or os.getenv("OPENAI_API_KEY", ""),
            base_url=base_url if base_url else None,
        )
        self._vectorstore: Chroma | None = None

    async def initialize(self):
        """加载已有向量存储，不存在则重建"""
        os.makedirs(self.persist_path, exist_ok=True)
        os.makedirs(self.docs_path, exist_ok=True)

        try:
            if os.path.exists(self.persist_path) and os.listdir(self.persist_path):
                self._vectorstore = Chroma(
                    persist_directory=self.persist_path,
                    embedding_function=self.embeddings,
                )
                logger.info(
                    f"Loaded existing Chroma index from {self.persist_path}"
                )
            else:
                await self.rebuild()
        except Exception as e:
            logger.warning(f"Failed to load Chroma index: {e}, rebuilding...")
            await self.rebuild()

    async def rebuild(self):
        """重建整个向量索引"""
        documents = []

        # 从 docs_path 加载文档
        if os.path.isdir(self.docs_path):
            for filename in os.listdir(self.docs_path):
                filepath = os.path.join(self.docs_path, filename)
                if os.path.isfile(filepath):
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                    except UnicodeDecodeError:
                        continue
                    documents.append(content)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, chunk_overlap=50
        )
        chunks = []
        for doc in documents:
            chunks.extend(text_splitter.split_text(doc))

        if not chunks:
            logger.warning("No documents found for knowledge base, vectorstore not created")
            return

        self._vectorstore = Chroma.from_texts(
            chunks,
            self.embeddings,
            persist_directory=self.persist_path,
        )
        logger.info(f"Knowledge base rebuilt: {len(documents)} docs -> {len(chunks)} chunks")

    # ── 增量操作 ──────────────────────────────────────────────────

    def _split_text(self, text: str) -> list[str]:
        """将文档文本分割为 chunk"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, chunk_overlap=50
        )
        return text_splitter.split_text(text)

    async def _ensure_vectorstore(self, first_chunks: list[str], metadatas: list[dict]):
        """向量库不存在时用首批数据创建"""
        self._vectorstore = Chroma.from_texts(
            first_chunks,
            self.embeddings,
            metadatas=metadatas,
            persist_directory=self.persist_path,
        )
        logger.info(f"Knowledge base: created vectorstore with {len(first_chunks)} chunks")

    async def add_document(self, doc_id: int, title: str, content: str):
        """
        增量添加文档：分块后插入 Chroma，无需全量重建。
        如果向量库还未创建（首次添加），则用本文档创建。
        """
        chunks = self._split_text(content)
        if not chunks:
            return 0

        metadatas = [{"doc_id": str(doc_id), "title": title}] * len(chunks)

        if self._vectorstore is None:
            await self._ensure_vectorstore(chunks, metadatas)
        else:
            self._vectorstore.add_texts(chunks, metadatas=metadatas)

        logger.info(f"Knowledge base: added doc {doc_id} ({title}) -> {len(chunks)} chunks")
        return len(chunks)

    async def delete_document(self, doc_id: int):
        """
        按 doc_id 删除文档的所有 chunk。
        Chroma 的 .delete() 支持按 metadata filter 删除。
        """
        if self._vectorstore is None:
            logger.warning("Vector store not initialized, skipping delete")
            return

        try:
            # Chroma delete by metadata filter
            self._vectorstore._collection.delete(
                where={"doc_id": str(doc_id)}
            )
            logger.info(f"Knowledge base: deleted doc {doc_id} from index")
        except Exception as e:
            logger.warning(f"Failed to delete doc {doc_id} from Chroma: {e}")

    async def search(self, query: str, k: int = 3):
        """检索相关文档片段"""
        if self._vectorstore is None:
            return []
        try:
            return self._vectorstore.similarity_search(query, k=k)
        except Exception as e:
            logger.warning(f"Knowledge base search error: {e}")
            return []
