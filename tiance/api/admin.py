from fastapi import APIRouter, Request

from tiance.errors import data_response


router = APIRouter(prefix="/api/admin")


def _service(request: Request):
    return request.app.state.admin_service


@router.get("/data-sources")
def list_data_sources(request: Request):
    return data_response(_service(request).list_data_sources())


@router.get("/db/tables")
def list_tables(request: Request):
    return data_response(_service(request).list_tables())


@router.get("/db/tables/{table_name}/rows")
def get_table_rows(
    table_name: str,
    request: Request,
    limit: int = 200,
    offset: int = 0,
):
    rows = _service(request).get_table_rows(table_name, limit=limit, offset=offset)
    return data_response(rows)


@router.post("/refresh/{task_name}", status_code=202)
def refresh(task_name: str, request: Request):
    return data_response(_service(request).trigger_refresh(task_name))
