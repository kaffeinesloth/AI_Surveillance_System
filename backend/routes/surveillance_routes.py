from fastapi import APIRouter, Depends, HTTPException, Response

from backend.app.schemas import (
    LatestFrameAnalysis,
    SurveillanceStartRequest,
    SurveillanceStatus,
)
from backend.services.surveillance_manager import (
    LiveSurveillanceManager,
    SurveillanceAlreadyRunningError,
    SurveillanceCameraInactiveError,
    SurveillanceCameraNotFoundError,
    SurveillanceNotRunningError,
    SurveillanceStopTimeoutError,
    surveillance_manager,
)
from backend.services.video_analysis_manager import (
    VideoAnalysisManager,
    video_analysis_manager,
)

router = APIRouter(prefix="/surveillance", tags=["surveillance"])


def get_surveillance_manager() -> LiveSurveillanceManager:
    return surveillance_manager


def get_video_analysis_activity_manager() -> VideoAnalysisManager:
    return video_analysis_manager


@router.post("/start", response_model=SurveillanceStatus)
def start_surveillance(
    request: SurveillanceStartRequest,
    manager: LiveSurveillanceManager = Depends(get_surveillance_manager),
    video_manager: VideoAnalysisManager = Depends(
        get_video_analysis_activity_manager
    ),
):
    if video_manager.has_active_job():
        raise HTTPException(
            status_code=409,
            detail="Wait for uploaded-video analysis to finish or cancel it",
        )
    try:
        return manager.start(request.camera_id)
    except SurveillanceCameraNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        SurveillanceAlreadyRunningError,
        SurveillanceCameraInactiveError,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/stop", response_model=SurveillanceStatus)
def stop_surveillance(
    manager: LiveSurveillanceManager = Depends(get_surveillance_manager),
):
    try:
        return manager.stop()
    except SurveillanceNotRunningError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SurveillanceStopTimeoutError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/status", response_model=SurveillanceStatus)
def get_surveillance_status(
    manager: LiveSurveillanceManager = Depends(get_surveillance_manager),
):
    return manager.status()


@router.get("/latest", response_model=LatestFrameAnalysis)
def get_latest_analysis(
    manager: LiveSurveillanceManager = Depends(get_surveillance_manager),
):
    latest = manager.latest_analysis()
    if latest is None:
        raise HTTPException(
            status_code=404,
            detail="No live analysis result is available",
        )

    analysis = latest.analysis
    return {
        "frame_index": analysis.frame_index,
        "timestamp_seconds": analysis.timestamp_seconds,
        "width": analysis.width,
        "height": analysis.height,
        "tracks": [
            {
                "track_id": track.track_id,
                "bounding_box": {
                    "x1": track.bounding_box.x1,
                    "y1": track.bounding_box.y1,
                    "x2": track.bounding_box.x2,
                    "y2": track.bounding_box.y2,
                },
                "person_confidence": track.person_confidence,
                "status": track.status,
                "member_id": track.member_id,
                "member_name": (
                    latest.member_names.get(track.member_id)
                    if track.member_id is not None
                    else None
                ),
                "similarity": track.similarity,
                "face_confidence": track.face_confidence,
            }
            for track in analysis.tracks
        ],
    }


@router.get("/frame")
def get_latest_frame(
    manager: LiveSurveillanceManager = Depends(get_surveillance_manager),
):
    frame = manager.latest_frame_jpeg()
    if frame is None:
        raise HTTPException(
            status_code=404,
            detail="No live frame is available",
        )
    return Response(
        content=frame,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )
