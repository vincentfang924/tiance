from datetime import date

from fastapi import APIRouter, Query, Request

from tiance.errors import data_response


router = APIRouter(prefix="/api/market")


def _service(request: Request):
    return request.app.state.market_service


@router.get("/{secucode}/kline")
def get_kline(
    secucode: str,
    request: Request,
    start: date | None = None,
    end: date | None = None,
    freq: str = "D",
    ma: str = Query(default="5,10,20,60"),
):
    result = _service(request).get_kline(
        secucode,
        start=start,
        end=end,
        freq=freq,
        ma=_parse_ma(ma),
    )
    return data_response(result.model_dump(mode="json"))


def _parse_ma(value: str) -> list[int]:
    return [int(item) for item in value.split(",") if item.strip()]
