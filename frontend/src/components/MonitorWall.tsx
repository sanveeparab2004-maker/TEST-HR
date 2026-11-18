import React, { useState, useEffect, useRef } from "react";
import {
  ShieldAlert, Users, Video, Wifi, WifiOff, Bell, BellOff,
  Filter, ArrowUpDown, MessageSquare, Check, X, AlertTriangle,
  Clock, Eye, Maximize2, ExternalLink
} from "lucide-react";
import { UserSession } from "../types";

interface CandidateTileData {
  attempt_id: number;
  employee_code: string;
  full_name: string;
  status: string;
  started_at: string;
  deadline_at: string;
  remaining_seconds: number;
  answered_count: number;
  total_questions: number;
  warning_count: number;
  violation_count: number;
  status_ring: "green" | "amber" | "red" | "grey";
  is_online: boolean;
  last_violation_at?: string;
  snapshot_frame?: string;
  is_snapshot_mode?: boolean;
}

interface ViolationEvent {
  id: number;
  attempt_id: number;
  employee_code: string;
  full_name: string;
  kind: string;
  warning_count: number;
  warning_tier: string;
  at: string;
}

interface MonitorWallProps {
  user: UserSession;
  onLogout: () => void;
}

export const MonitorWall: React.FC<MonitorWallProps> = ({ user, onLogout }) => {
  const [candidates, setCandidates] = useState<CandidateTileData[]>([]);
  const [liveEvents, setLiveEvents] = useState<ViolationEvent[]>([]);
  const [filter, setFilter] = useState<"all" | "flagged" | "offline">("all");
  const [sortByWarnings, setSortByWarnings] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(true);

  // Enlarged candidate drawer
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateTileData | null>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [loadingTimeline, setLoadingTimeline] = useState(false);

  // Broadcast / Direct message modal
  const [messageTarget, setMessageTarget] = useState<CandidateTileData | null>(null);
  const [broadcastOpen, setBroadcastOpen] = useState(false);
  const [proctorMsgText, setProctorMsgText] = useState("");
  const [sendingMsg, setSendingMsg] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const peerConnections = useRef<Record<number, RTCPeerConnection>>({});
  const videoRefs = useRef<Record<number, HTMLVideoElement | null>>({});
  const [remoteStreams, setRemoteStreams] = useState<Record<number, MediaStream>>({});

  // Initiate WebRTC peer connection to candidate
  const initiateWebRTC = async (attemptId: number) => {
    if (peerConnections.current[attemptId] || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    try {
      const pc = new RTCPeerConnection({
        iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
      });
      peerConnections.current[attemptId] = pc;

      // Request incoming video track
      pc.addTransceiver("video", { direction: "recvonly" });

      pc.ontrack = (event) => {
        if (event.streams && event.streams[0]) {
          const stream = event.streams[0];
          setRemoteStreams((prev) => ({ ...prev, [attemptId]: stream }));
        }
      };

      pc.onicecandidate = (event) => {
        if (event.candidate && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({
            type: "webrtc_candidate",
            target_attempt_id: attemptId,
            candidate: event.candidate
          }));
        }
      };

      pc.onconnectionstatechange = () => {
        if (pc.connectionState === "connected") {
          setCandidates((prev) =>
            prev.map((c) =>
              c.attempt_id === attemptId ? { ...c, is_snapshot_mode: false } : c
            )
          );
        } else if (pc.connectionState === "failed" || pc.connectionState === "disconnected") {
          setRemoteStreams((prev) => {
            const next = { ...prev };
            delete next[attemptId];
            return next;
          });
        }
      };

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      wsRef.current.send(JSON.stringify({
        type: "webrtc_offer",
        target_attempt_id: attemptId,
        sdp: offer
      }));
    } catch (e) {
      console.error("WebRTC initiation error:", e);
    }
  };

  // 1. Initial Candidates Fetch & Polling (every 5s)
  const fetchCandidates = async () => {
    try {
      const res = await fetch("/api/monitor/candidates", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("assess_token") || ""}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setCandidates((prev) => {
          // Merge existing snapshot frames if any
          const frameMap: Record<number, { frame?: string; snapMode?: boolean }> = {};
          prev.forEach((c) => {
            frameMap[c.attempt_id] = { frame: c.snapshot_frame, snapMode: c.is_snapshot_mode };
          });
          return data.map((c: any) => ({
            ...c,
            snapshot_frame: frameMap[c.attempt_id]?.frame,
            is_snapshot_mode: frameMap[c.attempt_id]?.snapMode,
          }));
        });
      }
    } catch {}
  };

  useEffect(() => {
    fetchCandidates();
    const interval = setInterval(fetchCandidates, 5000);
    return () => clearInterval(interval);
  }, []);

  // 2. Connect WebSocket Signalling
  useEffect(() => {
    const token = localStorage.getItem("assess_token");
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/signaling?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = async (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "violation_alert") {
          // New violation event pushed in real-time
          const newEv: ViolationEvent = {
            id: msg.violation_id,
            attempt_id: msg.attempt_id,
            employee_code: msg.employee_code,
            full_name: msg.full_name,
            kind: msg.kind,
            warning_count: msg.warning_count,
            warning_tier: msg.warning_tier,
            at: msg.at,
          };
          setLiveEvents((prev) => [newEv, ...prev.slice(0, 49)]);

          // Update candidate tile in-place
          setCandidates((prev) =>
            prev.map((c) => {
              if (c.attempt_id === msg.attempt_id) {
                return {
                  ...c,
                  warning_count: msg.warning_count,
                  violation_count: c.violation_count + 1,
                  status_ring: msg.warning_count >= 4 ? "red" : "amber",
                  last_violation_at: msg.at,
                };
              }
              return c;
            })
          );

          if (soundEnabled) {
            playAlertSound();
          }
        } else if (msg.type === "webrtc_answer") {
          const attId = msg.attempt_id;
          const pc = peerConnections.current[attId];
          if (pc && msg.sdp) {
            try {
              await pc.setRemoteDescription(new RTCSessionDescription(msg.sdp));
            } catch (err) {
              console.error("Set remote description error:", err);
            }
          }
        } else if (msg.type === "webrtc_candidate") {
          const attId = msg.attempt_id;
          const pc = peerConnections.current[attId];
          if (pc && msg.candidate) {
            try {
              await pc.addIceCandidate(new RTCIceCandidate(msg.candidate));
            } catch (err) {
              console.error("Add ICE candidate error:", err);
            }
          }
        } else if (msg.type === "candidate_snapshot") {
          const attId = msg.attempt_id;
          // Attempt WebRTC initiation if not already started
          if (attId && !peerConnections.current[attId]) {
            initiateWebRTC(attId);
          }
          setCandidates((prev) =>
            prev.map((c) =>
              c.attempt_id === attId
                ? { ...c, snapshot_frame: msg.frame, is_snapshot_mode: !remoteStreams[attId] }
                : c
            )
          );
        } else if (msg.type === "candidate_online") {
          fetchCandidates();
          if (msg.attempt_id && !peerConnections.current[msg.attempt_id]) {
            initiateWebRTC(msg.attempt_id);
          }
        }
      } catch {}
    };

    return () => {
      ws.close();
      Object.values(peerConnections.current).forEach((pc) => pc.close());
    };
  }, [soundEnabled]);

  const playAlertSound = () => {
    try {
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
      gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.35);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.35);
    } catch {}
  };

  // 3. Candidate Timeline Drawer
  const handleOpenTimeline = async (candidate: CandidateTileData) => {
    setSelectedCandidate(candidate);
    setLoadingTimeline(true);
    try {
      const res = await fetch(`/api/monitor/candidate/${candidate.attempt_id}/timeline`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("assess_token") || ""}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setTimeline(data.timeline || []);
      }
    } catch {} finally {
      setLoadingTimeline(false);
    }
  };

  // Review a violation (Dismiss or Confirm)
  const handleReviewViolation = async (violationId: number, status: "CONFIRMED" | "DISMISSED") => {
    try {
      const res = await fetch(`/api/monitor/violation/${violationId}/review`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("assess_token") || ""}`,
        },
        body: JSON.stringify({ review_status: status }),
      });
      if (res.ok) {
        setTimeline((prev) =>
          prev.map((v) => (v.id === violationId ? { ...v, review_status: status } : v))
        );
      }
    } catch {}
  };

  // Send message
  const handleSendMessage = async () => {
    if (!proctorMsgText.trim()) return;
    setSendingMsg(true);
    try {
      await fetch("/api/monitor/message", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("assess_token") || ""}`,
        },
        body: JSON.stringify({
          attempt_id: messageTarget ? messageTarget.attempt_id : null,
          message: proctorMsgText.trim(),
        }),
      });
      setProctorMsgText("");
      setMessageTarget(null);
      setBroadcastOpen(false);
    } catch {} finally {
      setSendingMsg(false);
    }
  };

  // Filter & Sort
  const filteredCandidates = candidates
    .filter((c) => {
      if (filter === "flagged") return c.warning_count > 0;
      if (filter === "offline") return !c.is_online;
      return true;
    })
    .sort((a, b) => {
      if (sortByWarnings) return b.warning_count - a.warning_count;
      return a.employee_code.localeCompare(b.employee_code);
    });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Bar */}
      <header className="h-16 border-b border-slate-800 bg-slate-900/90 px-6 flex items-center justify-between sticky top-0 z-30 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-rose-600 flex items-center justify-center text-white shadow-md shadow-rose-600/20">
            <Video className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
              <span>Proctoring Command Wall</span>
              <span className="px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 text-[10px] font-mono border border-rose-500/30">
                LIVE
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Proctor: <span className="text-slate-200 font-medium">{user.fullName}</span> ({user.employeeCode})
            </p>
          </div>
        </div>

        {/* Controls & Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setBroadcastOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition-colors"
          >
            <MessageSquare className="w-3.5 h-3.5 text-brand-400" />
            <span>Broadcast Message</span>
          </button>

          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className={`p-2 rounded-lg border text-xs transition-colors ${
              soundEnabled
                ? "bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700"
                : "bg-slate-900 border-slate-800 text-slate-500"
            }`}
            title={soundEnabled ? "Mute Alert Audio" : "Unmute Alert Audio"}
          >
            {soundEnabled ? <Bell className="w-4 h-4 text-amber-400" /> : <BellOff className="w-4 h-4" />}
          </button>

          <button
            onClick={onLogout}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-rose-950/60 hover:text-rose-300 text-xs text-slate-300 border border-slate-700 transition-colors"
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* Main Grid + Live Activity Feed Split */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Candidate Video Tiles Grid */}
        <main className="flex-1 p-6 overflow-y-auto space-y-6">
          {/* Filter Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 pb-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-2">
                Candidates ({filteredCandidates.length})
              </span>

              <div className="flex items-center bg-slate-900 rounded-lg p-1 border border-slate-800 text-xs">
                <button
                  onClick={() => setFilter("all")}
                  className={`px-3 py-1 rounded-md font-medium transition-colors ${
                    filter === "all" ? "bg-slate-800 text-white" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  All
                </button>
                <button
                  onClick={() => setFilter("flagged")}
                  className={`px-3 py-1 rounded-md font-medium transition-colors ${
                    filter === "flagged" ? "bg-amber-950/70 text-amber-300 border border-amber-600/40" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Flagged Only
                </button>
                <button
                  onClick={() => setFilter("offline")}
                  className={`px-3 py-1 rounded-md font-medium transition-colors ${
                    filter === "offline" ? "bg-rose-950/70 text-rose-300 border border-rose-600/40" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Offline
                </button>
              </div>
            </div>

            <button
              onClick={() => setSortByWarnings(!sortByWarnings)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                sortByWarnings
                  ? "bg-amber-950/40 border-amber-500/50 text-amber-300"
                  : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
              }`}
            >
              <ArrowUpDown className="w-3.5 h-3.5" />
              <span>Sort by Warnings</span>
            </button>
          </div>

          {/* Grid Tiles */}
          {filteredCandidates.length === 0 ? (
            <div className="h-64 flex flex-col items-center justify-center text-center text-slate-500 border border-dashed border-slate-800 rounded-2xl">
              <Users className="w-8 h-8 text-slate-600 mb-2" />
              <p className="text-sm font-medium">No candidates matching current filter</p>
              <p className="text-xs text-slate-600 mt-1">Tiles will appear as candidates authenticate and begin</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filteredCandidates.map((c) => {
                const ringColors = {
                  green: "border-emerald-500/60 shadow-[0_0_15px_rgba(16,185,129,0.15)]",
                  amber: "border-amber-500 shadow-[0_0_20px_rgba(245,158,11,0.25)]",
                  red: "border-rose-500 shadow-[0_0_25px_rgba(239,68,68,0.35)] animate-pulse",
                  grey: "border-slate-800 opacity-60",
                };

                const mins = Math.floor(c.remaining_seconds / 60);
                const secs = c.remaining_seconds % 60;

                return (
                  <div
                    key={c.attempt_id}
                    onClick={() => handleOpenTimeline(c)}
                    className={`bg-slate-900 rounded-2xl border-2 overflow-hidden cursor-pointer transition-all hover:scale-[1.01] hover:border-slate-600 group relative flex flex-col justify-between ${
                      ringColors[c.status_ring]
                    }`}
                  >
                    {/* Tile Top Info */}
                    <div className="p-3 bg-slate-900/95 border-b border-slate-800 flex items-center justify-between text-xs">
                      <div>
                        <p className="font-bold text-white leading-tight truncate max-w-[140px]">
                          {c.full_name}
                        </p>
                        <p className="text-[11px] font-mono text-slate-400">{c.employee_code}</p>
                      </div>

                      <div className="text-right">
                        <span className="font-mono text-xs font-semibold text-slate-300">
                          {String(mins).padStart(2, "0")}:{String(secs).padStart(2, "0")}
                        </span>
                        <p className="text-[10px] text-slate-500 font-medium">
                          {c.answered_count}/{c.total_questions} Ans
                        </p>
                      </div>
                    </div>

                    {/* Camera / Snapshot Display */}
                    <div className="relative aspect-[4/3] bg-black flex items-center justify-center overflow-hidden">
                      {remoteStreams[c.attempt_id] ? (
                        <video
                          ref={(el) => {
                            if (el && remoteStreams[c.attempt_id] && el.srcObject !== remoteStreams[c.attempt_id]) {
                              el.srcObject = remoteStreams[c.attempt_id];
                              el.play().catch(() => {});
                            }
                          }}
                          autoPlay
                          playsInline
                          muted
                          className="w-full h-full object-cover"
                        />
                      ) : c.snapshot_frame ? (
                        <img
                          src={c.snapshot_frame}
                          alt="Candidate Feed"
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="text-center p-4">
                          <Video className="w-8 h-8 text-slate-700 mx-auto mb-2 animate-pulse" />
                          <p className="text-[11px] text-slate-500">Connecting Camera Feed...</p>
                        </div>
                      )}

                      {/* WebRTC Live vs Snapshot Fallback Badge */}
                      {remoteStreams[c.attempt_id] ? (
                        <span className="absolute top-2 left-2 bg-emerald-950/80 backdrop-blur-sm text-emerald-300 border border-emerald-500/40 text-[10px] font-semibold px-2 py-0.5 rounded-md flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                          WebRTC Live (30 FPS)
                        </span>
                      ) : c.is_snapshot_mode ? (
                        <span className="absolute top-2 left-2 bg-slate-900/80 backdrop-blur-sm text-amber-300 border border-amber-500/40 text-[10px] font-semibold px-2 py-0.5 rounded-md flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                          Live Feed (1s)
                        </span>
                      ) : null}

                      {/* Status / Warning Pill */}
                      <div className="absolute bottom-2 right-2 flex items-center gap-1.5">
                        {c.warning_count > 0 && (
                          <span
                            className={`px-2 py-0.5 rounded-md text-[10px] font-bold ${
                              c.warning_count >= 4
                                ? "bg-rose-600 text-white animate-pulse"
                                : "bg-amber-500 text-slate-950"
                            }`}
                          >
                            {c.warning_count >= 4 ? "FINAL WARN" : `WARN ${c.warning_count}/3`}
                          </span>
                        )}
                        <span
                          className={`w-2.5 h-2.5 rounded-full ${
                            c.is_online ? "bg-emerald-500" : "bg-rose-500"
                          }`}
                          title={c.is_online ? "Candidate Online" : "Candidate Disconnected"}
                        ></span>
                      </div>
                    </div>

                    {/* Tile Footer Actions */}
                    <div className="p-2.5 bg-slate-900/90 border-t border-slate-800/80 flex items-center justify-between text-xs">
                      <span className="text-[11px] text-slate-400">
                        {c.violation_count} event{c.violation_count === 1 ? "" : "s"}
                      </span>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setMessageTarget(c);
                        }}
                        className="p-1 text-slate-400 hover:text-brand-400 hover:bg-slate-800 rounded transition-colors"
                        title="Send Direct Proctor Message"
                      >
                        <MessageSquare className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </main>

        {/* Right: Rolling Live Events Feed */}
        <aside className="w-80 border-l border-slate-800 bg-slate-900/60 p-4 flex flex-col justify-between overflow-hidden hidden lg:flex">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Live Incident Stream
              </h3>
              <span className="text-[10px] font-mono text-slate-500">
                {liveEvents.length} events
              </span>
            </div>

            <div className="mt-3 space-y-2.5 overflow-y-auto max-h-[calc(100vh-140px)] pr-1">
              {liveEvents.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-10">
                  No security incidents detected yet.
                </p>
              ) : (
                liveEvents.map((ev) => (
                  <div
                    key={`${ev.id}-${ev.at}`}
                    className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800/80 space-y-1 text-xs animate-fadeIn"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-200 truncate max-w-[130px]">
                        {ev.full_name}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">
                        {new Date(ev.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-amber-400 font-mono font-medium text-[11px]">
                        {ev.kind}
                      </span>
                      <span
                        className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                          ev.warning_tier === "FINAL_WARNING"
                            ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                            : "bg-amber-500/20 text-amber-300"
                        }`}
                      >
                        {ev.warning_tier}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </aside>
      </div>

      {/* Candidate Detailed Timeline Drawer */}
      {selectedCandidate && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-lg bg-slate-900 border-l border-slate-800 h-full p-6 flex flex-col justify-between overflow-y-auto animate-fadeIn">
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                <div>
                  <h3 className="text-base font-bold text-white">{selectedCandidate.full_name}</h3>
                  <p className="text-xs text-slate-400 font-mono mt-0.5">
                    {selectedCandidate.employee_code} • {selectedCandidate.warning_count} Warnings
                  </p>
                </div>
                <button
                  onClick={() => setSelectedCandidate(null)}
                  className="p-2 text-slate-400 hover:text-white rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Timeline Items */}
              <div className="mt-6 space-y-4">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Incident History ({timeline.length})
                </h4>

                {loadingTimeline ? (
                  <p className="text-xs text-slate-500 py-6 text-center">Loading incident records...</p>
                ) : timeline.length === 0 ? (
                  <p className="text-xs text-emerald-400 py-6 text-center">
                    Clean proctoring log. No recorded violations.
                  </p>
                ) : (
                  timeline.map((item) => (
                    <div
                      key={item.id}
                      className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3"
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-mono font-bold text-amber-400">{item.kind}</span>
                        <span className="text-[11px] text-slate-500">
                          {new Date(item.at).toLocaleTimeString()}
                        </span>
                      </div>

                      {item.snapshot && (
                        <div className="aspect-[4/3] rounded-lg overflow-hidden border border-slate-800 bg-black">
                          <img src={item.snapshot} alt="Violation" className="w-full h-full object-cover" />
                        </div>
                      )}

                      <div className="flex items-center justify-between pt-2 border-t border-slate-800/60 text-xs">
                        <span className="text-slate-400">
                          Review: <span className="font-semibold text-slate-200">{item.review_status}</span>
                        </span>

                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => handleReviewViolation(item.id, "DISMISSED")}
                            className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] text-slate-300"
                          >
                            Dismiss
                          </button>
                          <button
                            onClick={() => handleReviewViolation(item.id, "CONFIRMED")}
                            className="px-2 py-1 rounded bg-rose-950 hover:bg-rose-900 text-[11px] text-rose-300 border border-rose-800"
                          >
                            Confirm
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="pt-4 border-t border-slate-800">
              <button
                onClick={() => {
                  setMessageTarget(selectedCandidate);
                  setSelectedCandidate(null);
                }}
                className="w-full py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium text-xs transition-colors flex items-center justify-center gap-2"
              >
                <MessageSquare className="w-4 h-4" />
                <span>Send Message to Candidate</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Proctor Message Modal (Direct or Broadcast) */}
      {(messageTarget || broadcastOpen) && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 max-w-md w-full rounded-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h3 className="font-bold text-white text-sm">
                {messageTarget
                  ? `Message to ${messageTarget.full_name} (${messageTarget.employee_code})`
                  : "Broadcast Message to All Active Candidates"}
              </h3>
              <button
                onClick={() => {
                  setMessageTarget(null);
                  setBroadcastOpen(false);
                }}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <textarea
              rows={3}
              value={proctorMsgText}
              onChange={(e) => setProctorMsgText(e.target.value)}
              placeholder="e.g. Please ensure your webcam stays centered on your face."
              className="w-full p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder:text-slate-500 focus:border-brand-500 outline-none resize-none"
            />

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => {
                  setMessageTarget(null);
                  setBroadcastOpen(false);
                }}
                className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleSendMessage}
                disabled={sendingMsg || !proctorMsgText.trim()}
                className="px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold disabled:opacity-50"
              >
                {sendingMsg ? "Sending..." : "Send Message"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
