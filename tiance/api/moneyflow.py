from fastapi import APIRouter, Query, Request

from tiance.errors import data_response


router = APIRouter(prefix="/api/moneyflow")


def _service(request: Request):
    return request.app.state.moneyflow_service


@router.get("/{secucode}/concepts")
def get_concept_moneyflow(
    secucode: str,
    request: Request,
    sort_window: int = Query(default=20, ge=1, le=20),
    limit: int = Query(default=12, ge=1, le=30),
):
    result = _service(request).get_concept_moneyflow(
        secucode,
        sort_window=sort_window,
        limit=limit,
    )
    return data_response(result)
