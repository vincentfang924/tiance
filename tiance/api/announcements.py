from datetime import date, timedelta

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
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=50, ge=1, le=200),
):
    since = date.today() - timedelta(days=days)
    rows = _service(request).list_for_stock(secucode, bucket=bucket, since=since, limit=limit)
    return data_response(rows)


@router.get("/{secucode}/{ann_id:path}")
def get_announcement_detail(secucode: str, ann_id: str, request: Request):
    row = _service(request).get_detail(secucode, ann_id)
    return data_response(row)


@router.post("/{secucode}/refresh")
def refresh_announcements(
    secucode: str,
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
):
    since = date.today() - timedelta(days=days)
    inserted = _service(request).fetch_for(secucode, since=since)
    return data_response({"secucode": secucode, "inserted": inserted})
