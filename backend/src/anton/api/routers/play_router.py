from fastapi import APIRouter, Response

from anton.api.content_disposition import attachment_header
from anton.api.dependencies import PlayServiceDep
from anton.api.dto.play_dto import SceneTextEdit
from anton.domain.models import Play


router = APIRouter(prefix="/story/play", tags=["play"])


@router.get("")
async def get_play(service: PlayServiceDep) -> Play:
    """Return the whole play: title page, Dramatis Personae and every act with its scenes."""
    return service.get_play()


@router.put("/acts/{number}/scenes/{scene_number}/text")
async def edit_scene_text(number: int, scene_number: int, body: SceneTextEdit, service: PlayServiceDep) -> Play:
    """Save a final correction of one scene's text and return the updated play."""
    return service.edit_scene_text(number, scene_number, body.text)


@router.get("/pdf")
def export_pdf(service: PlayServiceDep) -> Response:
    """Return the finished play as an A4 PDF to download.

    It is a plain function, so FastAPI runs the CPU-bound typesetting in a worker thread, not in the event loop.
    """
    file_name, pdf_bytes = service.export_pdf()
    headers = {"Content-Disposition": attachment_header(file_name)}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
