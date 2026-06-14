NOISY_CLASS_NAMES = {"价格", "其他", "地域", "政策"}
NOISY_CONCEPT_NAMES = {
    "融资融券",
    "转融券标的",
    "深股通",
    "沪股通",
    "纳入富时罗素",
    "纳入MSCI",
    "高价股",
    "大盘股",
    "昨日高振幅",
}


class MoneyflowService:
    def __init__(self, tianyan_client) -> None:
        self.tianyan_client = tianyan_client

    def get_concept_moneyflow(
        self,
        secucode: str,
        sort_window: int = 20,
        limit: int = 12,
    ) -> dict:
        safe_window = sort_window if sort_window in {1, 5, 20} else 20
        safe_limit = max(1, min(limit, 30))
        concepts = [
            concept
            for concept in self.tianyan_client.get_stock_concepts(secucode)
            if is_business_concept(concept)
        ]
        concept_by_code = {int(item["concept_code"]): item for item in concepts[:16]}
        if not concept_by_code:
            return {
                "secucode": secucode,
                "latest_trade_date": None,
                "sort_window": safe_window,
                "items": [],
            }

        moneyflow = self.tianyan_client.get_concept_moneyflow(list(concept_by_code))
        rows = []
        for row in moneyflow.get("items", []):
            concept_code = int(row["concept_code"])
            concept = concept_by_code.get(concept_code)
            if concept is None:
                continue
            rows.append(
                {
                    **concept,
                    "concept_code": concept_code,
                    "stock_count": int(row.get("stock_count") or 0),
                    "flow_1d": _number(row.get("flow_1d")),
                    "flow_5d": _number(row.get("flow_5d")),
                    "flow_20d": _number(row.get("flow_20d")),
                }
            )

        key = f"flow_{safe_window}d"
        rows.sort(key=lambda item: abs(item[key] or 0), reverse=True)
        return {
            "secucode": secucode,
            "latest_trade_date": moneyflow.get("latest_trade_date"),
            "sort_window": safe_window,
            "items": rows[:safe_limit],
        }


def is_business_concept(concept: dict) -> bool:
    class_name = str(concept.get("class_name") or "")
    concept_name = str(concept.get("concept_name") or "")
    if class_name in NOISY_CLASS_NAMES:
        return False
    if concept_name in NOISY_CONCEPT_NAMES:
        return False
    if concept_name.startswith("昨日"):
        return False
    return True


def _number(value) -> float:
    try:
        return round(float(value or 0), 4)
    except (TypeError, ValueError):
        return 0.0
