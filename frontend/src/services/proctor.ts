import { api } from "./api";

export interface ProctorCallbacks {
  onWarning: (tier: string, message: string, kind: string, remainingWarnings: number) => void;
  onPostFinalNoted: (kind: string, message: string) => void;
  onCameraOff: (isOff: boolean) => void;
  onProctorMessage?: (message: string, sender: string) => void;
}

export class ProctorEngine {
  private stream: MediaStream | null = null;
  private videoEl: HTMLVideoElement | null = null;
  private canvasEl: HTMLCanvasElement | null = null;
  private callbacks: ProctorCallbacks;

  private isRunning = false;
  private heartbeatInterval: any = null;
  private faceAnalysisInterval: any = null;
  private snapshotFallbackInterval: any = null;
  private ws: WebSocket | null = null;
  private peerConnection: RTCPeerConnection | null = null;
  private webrtcConnected = false;

  // Debounce & Cooldown trackers
  private lastViolationTime: Record<string, number> = {};
  private lookingAwayCooldownUntil = 0;
  private lookingAwaySecondsCount = 0;
  private noFaceSecondsCount = 0;
  private windowBlurTimer: any = null;

  constructor(callbacks: ProctorCallbacks) {
    this.callbacks = callbacks;
    this.canvasEl = document.createElement("canvas");
    this.canvasEl.width = 320;
    this.canvasEl.height = 240;
  }

  public start(stream: MediaStream) {
    if (this.isRunning) return;
    this.isRunning = true;
    this.stream = stream;

    // Create offscreen video element for analysis
    this.videoEl = document.createElement("video");
    this.videoEl.autoplay = true;
    this.videoEl.playsInline = true;
    this.videoEl.muted = true;
    this.videoEl.srcObject = stream;
    this.videoEl.play().catch(() => {});

    this.attachEventListeners();
    this.startHeartbeat();
    this.startFaceAnalysis();
    this.connectSignaling();
  }

  public stop() {
    this.isRunning = false;
    this.detachEventListeners();
    if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
    if (this.faceAnalysisInterval) clearInterval(this.faceAnalysisInterval);
    if (this.snapshotFallbackInterval) clearInterval(this.snapshotFallbackInterval);
    if (this.windowBlurTimer) clearTimeout(this.windowBlurTimer);

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }

    if (this.videoEl) {
      this.videoEl.srcObject = null;
      this.videoEl = null;
    }
  }

  private connectSignaling() {
    const token = localStorage.getItem("assess_token");
    if (!token) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/signaling?token=${token}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onmessage = async (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === "proctor_message" && this.callbacks.onProctorMessage) {
            this.callbacks.onProctorMessage(msg.message, msg.sender || "Proctor");
          } else if (msg.type === "webrtc_offer") {
            // Monitor initiated WebRTC connection
            await this.handleWebRTCOffer(msg.sdp);
          } else if (msg.type === "webrtc_candidate" && this.peerConnection) {
            await this.peerConnection.addIceCandidate(new RTCIceCandidate(msg.candidate));
          }
        } catch {}
      };

      // Start live snapshots after 1 second if WebRTC is still negotiating
      setTimeout(() => {
        if (!this.webrtcConnected && this.isRunning) {
          this.startSnapshotFallback();
        }
      }, 1000);
    } catch {
      this.startSnapshotFallback();
    }
  }

  private startSnapshotFallback() {
    if (this.snapshotFallbackInterval) return;
    this.snapshotFallbackInterval = setInterval(() => {
      if (!this.isRunning || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;
      // If WebRTC is connected, no need to send WS frames
      if (this.webrtcConnected) return;

      const frame = this.captureSnapshot();
      if (frame) {
        this.ws.send(JSON.stringify({
          type: "candidate_snapshot",
          frame: frame
        }));
      }
    }, 1000); // 1-second interval for smooth live monitoring
  }

  private async handleWebRTCOffer(sdp: any) {
    if (!this.stream) return;
    try {
      const pc = new RTCPeerConnection({
        iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
      });
      this.peerConnection = pc;

      this.stream.getTracks().forEach((track) => {
        if (this.stream) pc.addTrack(track, this.stream);
      });

      pc.onicecandidate = (event) => {
        if (event.candidate && this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({
            type: "webrtc_candidate",
            candidate: event.candidate
          }));
        }
      };

      pc.onconnectionstatechange = () => {
        if (pc.connectionState === "connected") {
          this.webrtcConnected = true;
          if (this.snapshotFallbackInterval) {
            clearInterval(this.snapshotFallbackInterval);
            this.snapshotFallbackInterval = null;
          }
        } else if (pc.connectionState === "failed" || pc.connectionState === "disconnected") {
          this.webrtcConnected = false;
          this.startSnapshotFallback();
        }
      };

      await pc.setRemoteDescription(new RTCSessionDescription(sdp));
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);

      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({
          type: "webrtc_answer",
          sdp: answer
        }));
      }
    } catch {
      this.startSnapshotFallback();
    }
  }

  private attachEventListeners() {
    document.addEventListener("visibilitychange", this.handleVisibilityChange);
    window.addEventListener("blur", this.handleWindowBlur);
    window.addEventListener("focus", this.handleWindowFocus);
    document.addEventListener("fullscreenchange", this.handleFullscreenChange);
    document.addEventListener("copy", this.handleCopyPaste);
    document.addEventListener("cut", this.handleCopyPaste);
    document.addEventListener("paste", this.handleCopyPaste);
    document.addEventListener("contextmenu", this.handleContextMenu);
    window.addEventListener("keydown", this.handleKeyCombos, true);

    // Camera track listeners
    if (this.stream) {
      const vTrack = this.stream.getVideoTracks()[0];
      if (vTrack) {
        vTrack.onended = () => this.handleCameraTrackEnded();
        vTrack.onmute = () => this.handleCameraTrackEnded();
        vTrack.onunmute = () => this.callbacks.onCameraOff(false);
      }
    }
  }

  private detachEventListeners() {
    document.removeEventListener("visibilitychange", this.handleVisibilityChange);
    window.removeEventListener("blur", this.handleWindowBlur);
    window.removeEventListener("focus", this.handleWindowFocus);
    document.removeEventListener("fullscreenchange", this.handleFullscreenChange);
    document.removeEventListener("copy", this.handleCopyPaste);
    document.removeEventListener("cut", this.handleCopyPaste);
    document.removeEventListener("paste", this.handleCopyPaste);
    document.removeEventListener("contextmenu", this.handleContextMenu);
    window.removeEventListener("keydown", this.handleKeyCombos, true);
  }

  // --- Snapshot Generation (240x180 JPEG quality 0.5 for fast smooth streaming) ---
  private captureSnapshot(): string | undefined {
    if (!this.videoEl || !this.canvasEl) return undefined;
    try {
      const ctx = this.canvasEl.getContext("2d");
      if (!ctx) return undefined;
      ctx.drawImage(this.videoEl, 0, 0, 240, 180);
      return this.canvasEl.toDataURL("image/jpeg", 0.5);
    } catch {
      return undefined;
    }
  }

  // --- Send Violation Report ---
  private async reportViolation(kind: string, detail: Record<string, any> = {}) {
    if (!this.isRunning) return;

    // Check 5-second debounce for duplicate events of same kind
    const now = Date.now();
    const lastTime = this.lastViolationTime[kind] || 0;
    if (now - lastTime < 5000) return;
    this.lastViolationTime[kind] = now;

    const snapshot = this.captureSnapshot();

    try {
      const res = await fetch("/api/candidate/violation", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("assess_token") || ""}`,
        },
        body: JSON.stringify({
          kind: kind,
          detail: detail,
          snapshot: snapshot,
        }),
      });

      if (!res.ok) return;
      const data = await res.json();

      if (["WARNING_1", "WARNING_2", "WARNING_3", "FINAL_WARNING"].includes(data.warning_tier)) {
        const remaining = Math.max(0, 3 - data.warning_count);
        this.callbacks.onWarning(data.warning_tier, data.message, kind, remaining);
      } else if (data.warning_tier === "POST_FINAL_NOTED") {
        this.callbacks.onPostFinalNoted(kind, data.message);
      }
    } catch {}
  }

  // --- Event Handlers ---
  private handleVisibilityChange = () => {
    if (document.hidden) {
      this.reportViolation("TAB_SWITCH", { description: "Candidate switched browser tab" });
    }
  };

  private handleWindowBlur = () => {
    // Check if blur persists > 2s to ignore rapid OS micro-blurs
    if (this.windowBlurTimer) clearTimeout(this.windowBlurTimer);
    this.windowBlurTimer = setTimeout(() => {
      this.reportViolation("WINDOW_BLUR", { description: "Window lost focus for > 2 seconds" });
    }, 2000);
  };

  private handleWindowFocus = () => {
    if (this.windowBlurTimer) {
      clearTimeout(this.windowBlurTimer);
      this.windowBlurTimer = null;
    }
  };

  private handleFullscreenChange = () => {
    if (!document.fullscreenElement) {
      this.reportViolation("FULLSCREEN_EXIT", { description: "Candidate exited compulsory fullscreen mode" });
    }
  };

  private handleCopyPaste = (e: ClipboardEvent) => {
    e.preventDefault();
    this.reportViolation("COPY_PASTE", { action: e.type, description: "Prohibited clipboard action attempted" });
  };

  private handleContextMenu = (e: MouseEvent) => {
    e.preventDefault();
  };

  private handleKeyCombos = (e: KeyboardEvent) => {
    const key = e.key.toUpperCase();
    const isCtrl = e.ctrlKey || e.metaKey;

    // Block DevTools shortcuts and Print/Save
    if (
      key === "F12" ||
      (isCtrl && ["I", "J", "C", "U", "S", "P"].includes(key)) ||
      (isCtrl && e.shiftKey && ["I", "J", "C"].includes(key))
    ) {
      e.preventDefault();
      e.stopPropagation();
      this.reportViolation("DEV_TOOLS_KEY", { keyCombo: `${isCtrl ? "Ctrl+" : ""}${key}` });
    }
  };

  private handleCameraTrackEnded = () => {
    this.callbacks.onCameraOff(true);
    this.reportViolation("CAMERA_OFF", { description: "Camera track interrupted or revoked" });
  };

  // --- In-Browser Lightweight Face & Gaze Heuristics (1-second loop) ---
  private startFaceAnalysis() {
    this.faceAnalysisInterval = setInterval(() => {
      // Periodic check: camera track must remain live and active
      const vTrack = this.stream?.getVideoTracks()[0];
      const isLive = !!(vTrack && vTrack.readyState === "live" && !vTrack.muted && vTrack.enabled);
      if (!isLive) {
        this.callbacks.onCameraOff(true);
        return;
      } else {
        this.callbacks.onCameraOff(false);
      }

      if (!this.videoEl || !this.canvasEl || this.videoEl.readyState < 2) return;

      try {
        const ctx = this.canvasEl.getContext("2d");
        if (!ctx) return;

        ctx.drawImage(this.videoEl, 0, 0, 160, 120);
        const imgData = ctx.getImageData(0, 0, 160, 120);
        const data = imgData.data;

        // Centroid & Skin-tone detection
        let skinPixels = 0;
        let totalX = 0;
        let totalY = 0;

        for (let i = 0; i < data.length; i += 4) {
          const r = data[i];
          const g = data[i + 1];
          const b = data[i + 2];

          // Normalized skin tone thresholding
          if (r > 60 && g > 40 && b > 20 && r > g && r > b && Math.abs(r - g) > 15) {
            skinPixels++;
            const pixelIndex = i / 4;
            const x = pixelIndex % 160;
            const y = Math.floor(pixelIndex / 160);
            totalX += x;
            totalY += y;
          }
        }

        const now = Date.now();

        // 1. Check No Face (> 5s)
        if (skinPixels < 350) {
          this.noFaceSecondsCount++;
          if (this.noFaceSecondsCount >= 5) {
            this.noFaceSecondsCount = 0;
            this.reportViolation("NO_FACE", { skinPixelCount: skinPixels, description: "No face detected in camera for > 5s" });
          }
        } else {
          this.noFaceSecondsCount = 0;

          // 2. Check Gaze / Looking Away (> 4s, 15s cooldown)
          const avgX = totalX / skinPixels;
          const avgY = totalY / skinPixels;

          // If face centroid is significantly offset from center (160x120 -> center is 80, 60)
          const isOffset = avgX < 35 || avgX > 125 || avgY < 20 || avgY > 100;

          if (isOffset && now > this.lookingAwayCooldownUntil) {
            this.lookingAwaySecondsCount++;
            if (this.lookingAwaySecondsCount >= 4) {
              this.lookingAwaySecondsCount = 0;
              this.lookingAwayCooldownUntil = now + 15000; // 15-second cooldown
              this.reportViolation("LOOKING_AWAY", { avgX, avgY, description: "Candidate looking away from screen > 4s" });
            }
          } else {
            this.lookingAwaySecondsCount = 0;
          }
        }
      } catch {}
    }, 1000);
  }

  // --- Heartbeat Loop (5s) ---
  private startHeartbeat() {
    this.heartbeatInterval = setInterval(async () => {
      if (!this.isRunning) return;
      try {
        const vTrack = this.stream?.getVideoTracks()[0];
        const cameraActive = !!(vTrack && vTrack.readyState === "live" && !vTrack.muted);
        const fullscreenActive = !!document.fullscreenElement;

        await fetch("/api/candidate/heartbeat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("assess_token") || ""}`,
          },
          body: JSON.stringify({
            timestamp: Date.now() / 1000,
            fullscreen_active: fullscreenActive,
            camera_active: cameraActive,
          }),
        });
      } catch {}
    }, 5000);
  }
}
