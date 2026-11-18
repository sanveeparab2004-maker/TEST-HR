import json
import logging
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket

logger = logging.getLogger("assess.signaling")


class SignalingManager:
    """In-process WebRTC Signalling and Fallback Snapshot Relay.
    
    Manages WebSockets between candidates and authenticated monitors.
    """
    def __init__(self):
        # active monitor connections: set of WebSocket
        self.monitors: Set[WebSocket] = set()
        # active candidate connections: attempt_id -> WebSocket
        self.candidates: Dict[int, WebSocket] = {}
        # reverse map: WebSocket -> (role, attempt_id)
        self.connection_meta: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect_monitor(self, ws: WebSocket, user_code: str):
        await ws.accept()
        self.monitors.add(ws)
        self.connection_meta[ws] = {"role": "MONITOR", "code": user_code}
        logger.info(f"Monitor connected: {user_code}. Total monitors: {len(self.monitors)}")

    async def connect_candidate(self, ws: WebSocket, attempt_id: int, employee_code: str):
        # Single active WebSocket per attempt rule
        old_ws = self.candidates.get(attempt_id)
        if old_ws:
            try:
                await old_ws.send_json({
                    "type": "error",
                    "code": "MULTIPLE_TABS_BLOCKED",
                    "message": "Another tab was opened on this device. Closing this connection."
                })
                await old_ws.close(code=1008)
            except Exception:
                pass
            self.candidates.pop(attempt_id, None)
            self.connection_meta.pop(old_ws, None)

        await ws.accept()
        self.candidates[attempt_id] = ws
        self.connection_meta[ws] = {"role": "CANDIDATE", "attempt_id": attempt_id, "code": employee_code}
        logger.info(f"Candidate connected: {employee_code} (attempt {attempt_id}). Total candidates: {len(self.candidates)}")

        # Notify monitors of candidate online status
        await self.broadcast_to_monitors({
            "type": "candidate_online",
            "attempt_id": attempt_id,
            "employee_code": employee_code
        })

    def disconnect(self, ws: WebSocket):
        meta = self.connection_meta.pop(ws, None)
        if not meta:
            return

        role = meta.get("role")
        if role == "MONITOR":
            self.monitors.discard(ws)
            logger.info(f"Monitor disconnected: {meta.get('code')}")
        elif role == "CANDIDATE":
            attempt_id = meta.get("attempt_id")
            if attempt_id and self.candidates.get(attempt_id) == ws:
                self.candidates.pop(attempt_id, None)
                logger.info(f"Candidate disconnected: {meta.get('code')} (attempt {attempt_id})")

    async def broadcast_to_monitors(self, message: Dict[str, Any]):
        dead_monitors = []
        for ws in self.monitors:
            try:
                await ws.send_json(message)
            except Exception:
                dead_monitors.append(ws)
        for ws in dead_monitors:
            self.monitors.discard(ws)
            self.connection_meta.pop(ws, None)

    async def send_to_candidate(self, attempt_id: int, message: Dict[str, Any]):
        ws = self.candidates.get(attempt_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.candidates.pop(attempt_id, None)
                self.connection_meta.pop(ws, None)

    async def relay_webrtc(self, sender_ws: WebSocket, payload: Dict[str, Any]):
        """Relays WebRTC SDP offer/answer, ICE candidates, and fallback snapshots."""
        meta = self.connection_meta.get(sender_ws)
        if not meta:
            return

        role = meta.get("role")
        msg_type = payload.get("type")

        if role == "CANDIDATE":
            attempt_id = meta.get("attempt_id")
            # Forward WebRTC signaling / fallback snapshots from candidate to all monitors
            forward_msg = dict(payload)
            forward_msg["attempt_id"] = attempt_id
            forward_msg["employee_code"] = meta.get("code")
            await self.broadcast_to_monitors(forward_msg)

        elif role == "MONITOR":
            # Forward answer or ICE candidate from monitor to specific candidate
            target_attempt_id = payload.get("target_attempt_id")
            if target_attempt_id:
                await self.send_to_candidate(target_attempt_id, payload)


signaling_manager = SignalingManager()
