###############################################################################
#  LLM Service — 记忆管理 + 知识库 RAG + 弹幕回复生成
###############################################################################

import os
from typing import AsyncIterator

from openai import AsyncOpenAI
from app.config import load_settings
from app.utils.logger import logger

# 标点符号列表 — 用于流式分句
_PUNCTUATION = ",.!;:，。！？：；"

_cfg = load_settings()


class LLMService:
    """LLM 服务：人设驱动 + 短期记忆 + 知识库增强"""

    def __init__(self, persona: dict, llm_api_key: str = "", llm_base_url: str = "",
                 llm_model: str = "", embedding_api_key: str = "",
                 embedding_base_url: str = "", embedding_model: str = ""):
        self.persona = persona
        self.llm_api_key = llm_api_key or os.getenv("OPENAI_API_KEY", "")
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.embedding_api_key = embedding_api_key or os.getenv("EMBEDDING_API_KEY", "")
        self.embedding_base_url = embedding_base_url
        self.embedding_model = embedding_model

        if self.llm_api_key:
            self.client = AsyncOpenAI(
                api_key=self.llm_api_key,
                base_url=self.llm_base_url,
            )
        else:
            self.client = None
            logger.warning("LLM API key not configured — danmaku replies will be empty")

        # 短期记忆
        self._memory: dict[str, list[dict]] = {}
        self._memory_window = _cfg.memory_window_size
        # 知识库（延迟初始化）
        self._knowledge_base = None

    # ── 记忆管理 ──────────────────────────────────────────────────

    def _get_memory(self, user_id: str) -> list[dict]:
        """获取指定用户的对话历史"""
        if user_id not in self._memory:
            self._memory[user_id] = []
        return self._memory[user_id]

    def add_to_memory(self, user_id: str, role: str, content: str):
        """添加一条对话到记忆"""
        mem = self._get_memory(user_id)
        mem.append({"role": role, "content": content})
        # 保持窗口大小
        while len(mem) > self._memory_window * 2:  # user+assistant pairs
            mem.pop(0)

    def _build_messages(
        self, message: str, sender: str, kb_context: str = "", intent: str = "chat"
    ) -> list[dict]:
        """构建发给 LLM 的完整消息列表"""
        system_prompt = self._build_system_prompt(kb_context, intent)
        messages = [{"role": "system", "content": system_prompt}]
        # 添加该用户的对话历史
        messages.extend(self._get_memory(sender))
        # 添加当前消息（标注发送者）
        messages.append({"role": "user", "content": f"[{sender}] {message}"})
        return messages

    def _build_system_prompt(self, kb_context: str = "", intent: str = "chat") -> str:
        """根据人设构建 system prompt"""
        p = self.persona
        intent_instructions = {
            "product_sales": "价格信息 + 核心价值 + 自然引导",
            "product_info": "功能 + 解决的问题 + 应用场景",
            "objection": "理解顾虑 + 事实解释 + 降低顾虑",
            "chat": "自然互动，不要强行销售",
        }
        intent_instruction = intent_instructions.get(intent, intent_instructions["chat"])
        parts = [
            "你是“AI直播助手小智”，身份是专业AI数字人直播顾问。",
            "你的任务是帮助商家介绍产品、回答观众问题，并提供准确、有价值的信息。",
            "",
            "主播人格：",
            f"性格特点：{p.get('personality', '热情友好')}",
            f"说话风格：{p.get('style', '轻松活泼')}",
            f"知识范围：{p.get('knowledge_scope', '日常闲聊')}",
        ]
        forbidden = p.get("forbidden_topics", [])
        if forbidden:
            parts.append(f"禁止谈论以下话题：{'、'.join(forbidden)}")

        parts.extend([
            "",
            "事实约束（优先级高于销售表达）：",
            "1. 涉及产品信息时，优先且仅依据知识库中明确提供的事实回答。",
            "2. 价格、优惠、库存、活动和售后政策必须来自知识库，不得自行补充或推断。",
            "3. 知识库没有明确说明的信息不允许猜测，也不得把常识、经验或对话历史当作产品事实。",
            "4. 禁止虚构销量、客户案例、限时优惠、官方承诺和产品效果保证。",
            "5. 可以根据知识库中的明确功能解释其直接用途和合理使用场景，但不得夸大效果或作出保证。",
            "6. 如果观众询问的产品信息在知识库中没有明确答案，必须回复：这个信息目前产品资料里没有明确说明，我先不随便给你答案。如果你想了解其他方面，我可以根据已有资料帮你介绍。",
            "",
            "主播表达规则：",
            "1. 使用自然、口语化、简洁清楚且适合TTS播报的语言，保持亲切、专业和适度的直播互动感。",
            "2. 可以偶尔使用“家人们”“朋友们”“欢迎来到直播间”，但一次回复最多使用一个称呼，不要频繁使用。",
            "3. 禁止使用“绝绝子”“闭眼入”“无脑冲”“神器”“百分百有效”等夸张表达，避免过度营销。",
            "4. 不要使用表情符号和特殊字符，直接输出回复内容，不要添加任何前缀或说明。",
            "",
            "销售回答结构：",
            "1. 价格问题：先给出知识库中的准确价格，再说明一个核心功能或真实价值；只有知识库明确说明适合用户时才介绍适合人群，最后做轻度互动引导。",
            "2. 功能问题：说明知识库中的功能、它直接解决的问题以及合理应用场景，不得扩写成未经资料支持的效果承诺。",
            "3. 购买犹豫：先理解顾虑，再说明知识库中的真实价值和已有售后或保障信息，最后邀请观众继续了解，不制造紧迫感。",
            "4. 普通聊天：自然互动即可，可以结合上下文轻度引回直播主题，但不要强行销售。",
            "",
            f"当前用户意图：{intent}",
            f"本次回答结构：{intent_instruction}",
            "",
            "输出长度：",
            "普通问题回复2-3句话；复杂问题最多5句话；始终保持适合数字人连续播报。",
        ])

        if kb_context:
            parts.append(
                f"\n知识库参考资料开始\n{kb_context}\n知识库参考资料结束\n"
                "只使用以上资料中与当前问题直接相关、明确写出的产品事实。"
            )
        else:
            parts.append(
                "\n当前没有检索到知识库资料。涉及产品事实的问题必须使用资料不足回复，不得猜测。"
            )

        return "\n".join(parts)

    # ── 弹幕回复生成 ──────────────────────────────────────────────

    async def generate_reply(self, message: str, sender: str, intent: str = "chat") -> str:
        """为弹幕生成回复（非流式，直接返回完整结果）"""
        if self.client is None:
            return ""

        # 检索知识库
        kb_context = ""
        if self._knowledge_base:
            try:
                docs = await self._knowledge_base.search(message, k=2)
                if docs:
                    kb_context = "\n".join(d.page_content for d in docs)
            except Exception as e:
                logger.warning(f"Knowledge base search failed: {e}")

        messages = self._build_messages(message, sender, kb_context, intent)

        try:
            response = await self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                max_tokens=200,
                temperature=0.8,
            )
            reply = response.choices[0].message.content or ""
            reply = reply.strip()

            # 记录到记忆
            self.add_to_memory(sender, "user", message)
            self.add_to_memory(sender, "assistant", reply)

            return reply
        except Exception as e:
            logger.error(f"LLM generate failed: {e}")
            return ""

    async def generate_reply_stream(self, message: str, sender: str) -> AsyncIterator[str]:
        """流式生成弹幕回复，按标点分句 yield"""
        if self.client is None:
            yield ""
            return

        kb_context = ""
        if self._knowledge_base:
            try:
                docs = await self._knowledge_base.search(message, k=2)
                if docs:
                    kb_context = "\n".join(d.page_content for d in docs)
            except Exception:
                pass

        messages = self._build_messages(message, sender, kb_context)

        try:
            stream = await self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                max_tokens=200,
                temperature=0.8,
                stream=True,
            )

            buffer = ""
            full_reply = ""
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta is None:
                    continue

                for ch in delta:
                    buffer += ch
                    if ch in _PUNCTUATION and len(buffer) > 5:
                        sentence = buffer.strip()
                        if sentence:
                            yield sentence
                            full_reply += sentence
                        buffer = ""

            # 剩余内容
            if buffer.strip():
                yield buffer.strip()
                full_reply += buffer.strip()

            # 记录到记忆
            if full_reply:
                self.add_to_memory(sender, "user", message)
                self.add_to_memory(sender, "assistant", full_reply)

        except Exception as e:
            logger.error(f"LLM streaming failed: {e}")
            yield ""

    # ── 知识库 ────────────────────────────────────────────────────

    async def init_knowledge_base(self):
        """初始化知识库（从数据库加载文档并构建向量索引）"""
        try:
            from app.services.knowledge_base import KnowledgeBase
            self._knowledge_base = KnowledgeBase(
                docs_path=_cfg.knowledge_docs_path,
                persist_path=_cfg.chroma_persist_path,
                embedding_model=self.embedding_model,
                api_key=self.embedding_api_key,
                base_url=self.embedding_base_url,
            )
            await self._knowledge_base.initialize()
            logger.info("Knowledge base initialized")
        except Exception as e:
            logger.warning(f"Knowledge base init failed (will operate without KB): {e}")
            self._knowledge_base = None

    async def rebuild_knowledge_base(self):
        """重建知识库索引"""
        if self._knowledge_base:
            await self._knowledge_base.rebuild()
            logger.info("Knowledge base rebuilt")
