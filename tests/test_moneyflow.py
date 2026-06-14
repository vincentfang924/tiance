from tiance.services.moneyflow import MoneyflowService, is_business_concept


class FakeMoneyflowClient:
    def get_stock_concepts(self, secucode: str):
        assert secucode == "300502.SZ"
        return [
            {
                "concept_code": 11062211,
                "concept_name": "共封装光模块(CPO）",
                "class_name": "科技",
                "subclass_name": "新科技",
            },
            {
                "concept_code": 15030008,
                "concept_name": "融资融券",
                "class_name": "其他",
                "subclass_name": "特殊股票",
            },
            {
                "concept_code": 11102190,
                "concept_name": "光通信",
                "class_name": "科技",
                "subclass_name": "制造2025",
            },
        ]

    def get_concept_moneyflow(self, concept_codes: list[int]):
        assert concept_codes == [11062211, 11102190]
        return {
            "latest_trade_date": "20260612",
            "items": [
                {
                    "concept_code": 11062211,
                    "flow_1d": -860082.2174,
                    "flow_5d": -2648311.1115,
                    "flow_20d": 134566.1383,
                    "stock_count": 175,
                },
                {
                    "concept_code": 11102190,
                    "flow_1d": 12000,
                    "flow_5d": 23000,
                    "flow_20d": 230000,
                    "stock_count": 83,
                },
            ],
        }


def test_is_business_concept_filters_market_noise():
    assert is_business_concept({"concept_name": "共封装光模块(CPO）", "class_name": "科技"})
    assert not is_business_concept({"concept_name": "融资融券", "class_name": "其他"})
    assert not is_business_concept({"concept_name": "四川", "class_name": "地域"})
    assert not is_business_concept({"concept_name": "HALO", "class_name": "价格"})


def test_moneyflow_service_returns_related_concepts_sorted_by_window():
    service = MoneyflowService(FakeMoneyflowClient())

    result = service.get_concept_moneyflow("300502.SZ", sort_window=20, limit=10)

    assert result["secucode"] == "300502.SZ"
    assert result["latest_trade_date"] == "20260612"
    assert [item["concept_name"] for item in result["items"]] == [
        "光通信",
        "共封装光模块(CPO）",
    ]
    assert result["items"][0]["flow_20d"] == 230000
    assert result["items"][1]["flow_1d"] == -860082.2174
