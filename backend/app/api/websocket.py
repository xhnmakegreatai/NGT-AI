"""
WebSocket 实时通信

说明:实时进度推送尚未接入决策流程。为避免给出误导性的「假进度」,
连接后明确告知客户端改用 REST 轮询,并优雅关闭(诚实降级)。
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/decision")
async def websocket_decision(websocket: WebSocket):
    """实时决策分析 WebSocket(当前未启用,诚实降级为提示)。"""
    await websocket.accept()
    try:
        await websocket.send_json({
            "type": "info",
            "realtime_available": False,
            "message": "实时进度推送尚未启用,请改用 REST 接口轮询决策状态(详见 /docs)。",
        })
        await websocket.close()
    except WebSocketDisconnect:
        logger.info("WebSocket 连接已断开")
