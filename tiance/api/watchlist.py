from fastapi import APIRouter, Request

from tiance.errors import data_response
from tiance.models import AddStockRequest


router = APIRouter(prefix="/api/watchlist")


def _service(request: Request):
    return request.app.state.watchlist_service


@router.get("")
def list_watchlist(request: Request):
    rows = _service(request).list_watchlist()
    return data_response([row.model_dump(mode="json") for row in rows])


@router.post("")
def add_stock(payload: AddStockRequest, request: Request):
    row = _service(request).add_stock(payload.query, payload.group_id)
    return data_response(row.model_dump(mode="json"))


@router.get("/{secucode}")
def get_stock(secucode: str, request: Request):
    row = _service(request).get_stock(secucode)
    return data_response(row.model_dump(mode="json"))


@router.delete("/{secucode}")
def remove_stock(secucode: str, request: Request):
    _service(request).remove_stock(secucode)
    return data_response({"secucode": secucode})
