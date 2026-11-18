import React, { useState, useEffect, useRef } from "react";
import { Camera, CheckCircle2, XCircle, AlertCircle, Play, RefreshCw, Maximize, Wifi } from "lucide-react";
import { UserSession } from "../types";

interface SystemCheckPageProps {
  user: UserSession;
  onSystemCheckComplete: (stream: MediaStream) => void;
}

export const SystemCheckPage: React.FC<SystemCheckPageProps> = ({ user, onSystemCheckComplete }) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);

  const [cameraPass, setCameraPass] = useState(false);
  const [browserPass, setBrowserPass] = useState(false);
  const [fullscreenPass, setFullscreenPass] = useState(false);
  const [networkPass, setNetworkPass] = useState(navigator.onLine);

  const [cameraError, setCameraError] = useState<string | null>(null);
  const [countdown, setCountdown] = useState<number | null>(null);

  // Initialize checks
  useEffect(() => {
    // 1. Browser check
    const ua = navigator.userAgent.toLowerCase();
    const isChromeOrEdge = ua.includes("chrome") || ua.includes("edg");
    setBrowserPass(isChromeOrEdge);

    // 2. Fullscreen capability check
    const fsAvailable = !!(
      document.fullscreenEnabled ||
      (document as any).webkitFullscreenEnabled
    );
    setFullscreenPass(fsAvailable);

    // 3. Network listener
    const handleOnline = () => setNetworkPass(true);
    const handleOffline = () => setNetworkPass(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    // 4. Request Camera
    startCamera();

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  // Ensure video element receives stream when ready
  useEffect(() => {
    if (videoRef.current && stream) {
      if (videoRef.current.srcObject !== stream) {
        videoRef.current.srcObject = stream;
      }
      videoRef.current.play().catch(() => {});
    }
  }, [stream, cameraPass]);

  const startCamera = async () => {
    setCameraError(null);
    try {
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }

      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: "user",
        },
        audio: false,
      });

      setStream(mediaStream);
      setCameraPass(true);

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        videoRef.current.play().catch(() => {});
      }
    } catch (err: any) {
      setCameraPass(false);
      setCameraError(
        "Camera access is compulsory. Please allow camera permissions in your browser address bar and reload."
      );
    }
  };

  const allPassed = cameraPass && browserPass && fullscreenPass && networkPass;

  const handleStartExam = () => {
    if (!allPassed || !stream) return;
    setCountdown(5);
  };

  // Countdown handler
  useEffect(() => {
    if (countdown === null) return;
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    } else if (countdown === 0 && stream) {
      // Enter Fullscreen & Begin
      try {
        if (document.documentElement.requestFullscreen) {
          document.documentElement.requestFullscreen().catch(() => {});
        }
      } catch {}
      onSystemCheckComplete(stream);
    }
  }, [countdown, stream, onSystemCheckComplete]);

  return (
    <div className="max-w-4xl mx-auto py-10 px-6">
      {/* Step Indicator */}
      <div className="flex items-center justify-between mb-8 pb-4 border-b border-slate-200">
        <div className="flex items-center gap-2 text-slate-400">
          <span className="w-7 h-7 rounded-full bg-slate-100 text-xs font-medium flex items-center justify-center">1</span>
          <span className="text-sm font-medium">Rules & Consent</span>
        </div>
        <div className="w-12 h-0.5 bg-brand-600"></div>
        <div className="flex items-center gap-2">
          <span className="w-7 h-7 rounded-full bg-brand-600 text-white text-xs font-bold flex items-center justify-center">2</span>
          <span className="text-sm font-semibold text-slate-900">System Check</span>
        </div>
        <div className="w-12 h-0.5 bg-slate-200"></div>
        <div className="flex items-center gap-2 text-slate-400">
          <span className="w-7 h-7 rounded-full bg-slate-100 text-xs font-medium flex items-center justify-center">3</span>
          <span className="text-sm font-medium">Assessment</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
        {/* Left: Video Preview with Face Alignment Oval */}
        <div className="md:col-span-7 bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
              <Camera className="w-5 h-5 text-brand-600" />
              Camera Alignment Check
            </h3>
            {cameraPass && (
              <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                Active Feed
              </span>
            )}
          </div>

          <div className="relative aspect-video rounded-xl bg-slate-900 overflow-hidden flex items-center justify-center border border-slate-800">
            <video
              ref={(el) => {
                videoRef.current = el;
                if (el && stream && el.srcObject !== stream) {
                  el.srcObject = stream;
                  el.play().catch(() => {});
                }
              }}
              autoPlay
              playsInline
              muted
              className={`w-full h-full object-cover -scale-x-100 ${cameraPass ? "block" : "hidden"}`}
            />

            {cameraPass ? (
              /* Face Alignment Oval Guide */
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="w-44 h-56 rounded-[50%] border-2 border-dashed border-emerald-400/80 shadow-[0_0_20px_rgba(16,185,129,0.2)] flex items-center justify-center">
                  <p className="text-[11px] font-medium text-emerald-300 bg-slate-900/70 px-2 py-0.5 rounded-md backdrop-blur-sm">
                    Align Face Here
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-center p-6 space-y-3">
                <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 mx-auto">
                  <Camera className="w-6 h-6" />
                </div>
                <p className="text-xs text-slate-400 max-w-xs">
                  {cameraError || "Requesting camera permissions..."}
                </p>
                <button
                  onClick={startCamera}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Retry Camera
                </button>
              </div>
            )}
          </div>

          <p className="text-xs text-slate-500 text-center leading-relaxed">
            Ensure your face is clearly visible, well-lit, and positioned within the oval guide.
          </p>
        </div>

        {/* Right: Automated Verification List */}
        <div className="md:col-span-5 space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
            <h3 className="font-bold text-slate-900 text-base">Readiness Verification</h3>

            <div className="space-y-3.5">
              {/* Check 1: Camera */}
              <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-50 border border-slate-100">
                {cameraPass ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
                )}
                <div>
                  <p className="text-xs font-semibold text-slate-800">Webcam Permission</p>
                  <p className="text-[11px] text-slate-500">
                    {cameraPass ? "Video hardware connected" : "Compulsory for test participation"}
                  </p>
                </div>
              </div>

              {/* Check 2: Browser */}
              <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-50 border border-slate-100">
                {browserPass ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                )}
                <div>
                  <p className="text-xs font-semibold text-slate-800">Supported Browser</p>
                  <p className="text-[11px] text-slate-500">
                    {browserPass ? "Google Chrome / Microsoft Edge" : "Recommend modern Chrome or Edge"}
                  </p>
                </div>
              </div>

              {/* Check 3: Fullscreen */}
              <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-50 border border-slate-100">
                {fullscreenPass ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
                )}
                <div>
                  <p className="text-xs font-semibold text-slate-800">Fullscreen Capability</p>
                  <p className="text-[11px] text-slate-500">
                    {fullscreenPass ? "Browser supports full window lock" : "Cannot initiate fullscreen"}
                  </p>
                </div>
              </div>

              {/* Check 4: Network */}
              <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-50 border border-slate-100">
                {networkPass ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
                )}
                <div>
                  <p className="text-xs font-semibold text-slate-800">Network Connection</p>
                  <p className="text-[11px] text-slate-500">
                    {networkPass ? "Stable connection verified" : "Offline detected"}
                  </p>
                </div>
              </div>
            </div>

            {/* Countdown / Start Action */}
            <div className="pt-2">
              {countdown !== null ? (
                <div className="text-center py-4 rounded-xl bg-brand-50 border border-brand-200">
                  <p className="text-xs font-semibold text-brand-700">Entering Fullscreen & Starting in</p>
                  <p className="text-4xl font-bold text-brand-600 mt-1 font-mono">{countdown}</p>
                </div>
              ) : (
                <button
                  onClick={handleStartExam}
                  disabled={!allPassed}
                  className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium text-sm shadow-md shadow-brand-600/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  <Play className="w-4 h-4 fill-white" />
                  <span>Start 60-Minute Assessment</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
