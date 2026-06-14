from fastapi import APIRouter, Query, Request

from tiance.errors import data_response


router = APIRouter(prefix="/api/announcements")


def _service(request: Request):
    return request.app.state.announcement_service


@router.get("/{secucode}")
def list_announcements(
    secucode: str,
    request: Request,
    bucket: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    rows = _service(request).list_for_stock(secucode, bucket=bucket, limit=limit)
    return data_response(rows)
