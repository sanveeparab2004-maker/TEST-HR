import { api } from "./api";

export interface ProctorCallbacks {
  onWarning: (tier: string, message: string, kind: string, remainingWarnings: number, warningNumber?: number) => void;
  onPostFinalNoted: (kind: string, message: string) => void;
  onRestart?: (message: string, kind: string) => void;
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
    }, 4000); // 4-second interval for lightweight & smooth live monitoring without overloading Render
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

  // --- Snapshot Generation (160x120 JPEG quality 0.35 for fast smooth lightweight streaming) ---
  private captureSnapshot(): string | undefined {
    if (!this.videoEl || !this.canvasEl) return undefined;
    try {
      const ctx = this.canvasEl.getContext("2d");
      if (!ctx) return undefined;
      ctx.drawImage(this.videoEl, 0, 0, 160, 120);
      return this.canvasEl.toDataURL("image/jpeg", 0.35);
    } catch {
      return undefined;
    }
  }

  public resetViolationCooldown(kind?: string) {
    if (kind) {
      delete this.lastViolationTime[kind];
    } else {
      this.lastViolationTime = {};
    }
  }

  // --- Send Violation Report ---
  private async reportViolation(kind: string, detail: Record<string, any> = {}) {
    if (!this.isRunning) return;

    // Check 2.5-second debounce for duplicate events of same kind to avoid flood while remaining responsive
    const now = Date.now();
    const lastTime = this.lastViolationTime[kind] || 0;
    if (now - lastTime < 2500) return;
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

      if (data.action === "RESTART" || data.warning_tier === "RESTART") {
        if (this.callbacks.onRestart) {
          this.callbacks.onRestart(data.message || "Test restarted due to exceeding 5 warnings.", kind);
        } else {
          this.callbacks.onWarning("RESTART", data.message, kind, 0, 6);
        }
        return;
      }

      if (["WARNING_1", "WARNING_2", "WARNING_3", "FINAL_WARNING", "POST_FINAL_NOTED"].includes(data.warning_tier)) {
        const warnNum = data.warning_count || 1;
        const remaining = Math.max(0, 5 - warnNum);
        this.callbacks.onWarning(data.warning_tier, data.message, kind, remaining, warnNum);
      }
    } catch {}
  }

  // --- Event Handlers ---
  private handleVisibilityChange = () => {
    if (document.hidden) {
      // Immediate violation trigger on tab switch / minimize
      this.reportViolation("TAB_SWITCH", { description: "Candidate switched away from browser tab" });
    }
  };

  private handleWindowBlur = () => {
    // Detect window unfocus / alt-tab with quick 600ms debounce
    if (this.windowBlurTimer) clearTimeout(this.windowBlurTimer);
    this.windowBlurTimer = setTimeout(() => {
      this.reportViolation("TAB_SWITCH", { description: "Candidate unfocused or switched window" });
    }, 600);
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

  // --- In-Browser Face & Gaze Heuristics (1-second analysis loop) ---
  private startFaceAnalysis() {
    this.faceAnalysisInterval = setInterval(() => {
      // Periodic check: camera track must remain live and active
      const vTrack = this.stream?.getVideoTracks()[0];
      const isLive = !!(vTrack && vTrack.readyState === "live" && !vTrack.muted && vTrack.enabled);
      if (!isLive) {
        this.callbacks.onCameraOff(true);
        this.noFaceSecondsCount++;
        // If camera track is off or muted for 3 seconds, trigger warning
        if (this.noFaceSecondsCount >= 3) {
          this.noFaceSecondsCount = 0;
          this.reportViolation("CAMERA_OFF", { description: "Camera feed disabled, muted, or covered for > 3s" });
        }
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
        let centerSkinPixels = 0;
        let totalX = 0;
        let totalY = 0;

        for (let i = 0; i < data.length; i += 4) {
          const r = data[i];
          const g = data[i + 1];
          const b = data[i + 2];

          // Normalized skin tone thresholding in RGB space
          if (r > 60 && g > 40 && b > 20 && r > g && r > b && (r - g) > 12) {
            skinPixels++;
            const pixelIndex = i / 4;
            const x = pixelIndex % 160;
            const y = Math.floor(pixelIndex / 160);
            totalX += x;
            totalY += y;

            // Central 60% viewport where candidate's face naturally sits
            if (x >= 25 && x <= 135 && y >= 15 && y <= 105) {
              centerSkinPixels++;
            }
          }
        }

        const now = Date.now();

        // Face is present when sufficient skin pixels are detected in central region
        const isFacePresent = skinPixels >= 350 && centerSkinPixels >= 200;

        // 1. Check No Face (> 3s threshold)
        if (!isFacePresent) {
          this.noFaceSecondsCount++;
          if (this.noFaceSecondsCount >= 3) {
            this.noFaceSecondsCount = 0;
            this.reportViolation("NO_FACE", {
              skinPixelCount: skinPixels,
              centerSkinPixels: centerSkinPixels,
              description: "Face not detected in camera frame for > 3s"
            });
          }
        } else {
          this.noFaceSecondsCount = 0;

          // 2. Check Gaze / Looking Away (> 5s, 15s cooldown)
          const avgX = totalX / skinPixels;
          const avgY = totalY / skinPixels;

          // If face centroid is significantly offset from center (160x120 -> center is 80, 60)
          const isOffset = avgX < 20 || avgX > 140 || avgY < 12 || avgY > 108;

          if (isOffset && now > this.lookingAwayCooldownUntil) {
            this.lookingAwaySecondsCount++;
            if (this.lookingAwaySecondsCount >= 5) {
              this.lookingAwaySecondsCount = 0;
              this.lookingAwayCooldownUntil = now + 15000; // 15-second cooldown
              this.reportViolation("LOOKING_AWAY", { avgX, avgY, description: "Candidate looking away from screen > 5s" });
            }
          } else {
            this.lookingAwaySecondsCount = 0;
          }
        }
      } catch {}
    }, 1000);
  }

  // --- Heartbeat Loop (10s: keeps Render server actively warm without connection load) ---
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
    }, 10000);
  }
}
