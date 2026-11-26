"""Export API routes for generating and downloading verified Excel reports."""

from fastapi import Header, HTTPException
from fastapi.responses import FileResponse

from src.schemas.export import ExportRequest, ExportResponse
from src.security.authentication import AuthManager, AuthenticationError
from src.session.result_store import (
    ResultAccessDeniedError,
    ResultNotFoundError,
    default_result_store,
)
from src.tools.export.excel import (
    ExportNotFoundError,
    ExportSecurityError,
    default_excel_export_service,
)

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def export_report(
    body: ExportRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_netiq_api_key: str | None = Header(default=None, alias="X-NETIQ-API-KEY"),
) -> ExportResponse:
    """Generate an Excel (.xlsx) workbook from a verified backend result."""
    try:
        user = AuthManager.authenticate_incoming_request(authorization=authorization, api_key=x_netiq_api_key)
    except AuthenticationError as err:
        raise HTTPException(status_code=401, detail=str(err))

    try:
        result = default_result_store.get_result(
            result_id=body.result_id,
            username=user.username,
            is_admin=user.is_admin,
            permitted_circles=user.permitted_circles,
        )
    except ResultNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except ResultAccessDeniedError as err:
        raise HTTPException(status_code=403, detail=str(err))

    try:
        rec = default_excel_export_service.generate_excel(result)
    except ExportSecurityError as err:
        raise HTTPException(status_code=403, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to generate Excel export: {err}")

    return ExportResponse(
        status="COMPLETED",
        fileId=rec.file_id,
        fileName=rec.file_name,
        downloadUrl=f"/v1/export/{rec.file_id}",
        rowCount=rec.row_count,
    )


async def download_export(
    file_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_netiq_api_key: str | None = Header(default=None, alias="X-NETIQ-API-KEY"),
) -> FileResponse:
    """Download a previously generated Excel export after verifying ownership."""
    try:
        user = AuthManager.authenticate_incoming_request(authorization=authorization, api_key=x_netiq_api_key)
    except AuthenticationError as err:
        raise HTTPException(status_code=401, detail=str(err))

    try:
        rec = default_excel_export_service.get_file_record(
            file_id=file_id,
            username=user.username,
            is_admin=user.is_admin,
        )
    except ExportSecurityError as err:
        raise HTTPException(status_code=403, detail=str(err))
    except ExportNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))

    return FileResponse(
        path=str(rec.file_path),
        media_type=XLSX_MIME,
        filename=rec.file_name,
        headers={"Content-Disposition": f'attachment; filename="{rec.file_name}"'},
    )
