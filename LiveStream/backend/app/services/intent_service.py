###############################################################################
#  IntentService — 直播弹幕意图规则分类
###############################################################################


class IntentService:
    """使用关键词按固定优先级识别弹幕意图。"""

    _RULES = (
        (
            "objection",
            ("太贵", "贵", "考虑一下", "再看看", "不放心", "靠谱吗", "值不值", "担心", "不敢买"),
        ),
        (
            "product_sales",
            ("多少钱", "价格", "优惠", "活动", "怎么买", "购买", "下单", "付款"),
        ),
        (
            "product_info",
            ("功能", "作用", "有什么用", "怎么用", "怎么使用", "支持", "适合", "售后", "培训", "配置"),
        ),
    )

    def classify(self, message: str) -> str:
        """返回 product_sales / product_info / objection / chat。"""
        text = (message or "").strip().lower()
        for intent, keywords in self._RULES:
            if any(keyword in text for keyword in keywords):
                return intent
        return "chat"
