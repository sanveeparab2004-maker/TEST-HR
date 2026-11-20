import React, { useState, useEffect } from "react";
import { AlertTriangle, ShieldAlert, RotateCcw, Check } from "lucide-react";

interface WarningModalProps {
  isOpen: boolean;
  tier: string; // "WARNING_1" | "WARNING_2" | "WARNING_3" | "FINAL_WARNING" | "RESTART"
  kind: string;
  message: string;
  remainingWarnings: number;
  isRestart?: boolean;
  onAcknowledge: () => void;
}

export const WarningModal: React.FC<WarningModalProps> = ({
  isOpen,
  tier,
  kind,
  message,
  remainingWarnings,
  isRestart = false,
  onAcknowledge,
}) => {
  const [countdown, setCountdown] = useState(3);

  useEffect(() => {
    if (!isOpen) {
      setCountdown(3);
      return;
    }
    setCountdown(3);
    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isOpen]);

  if (!isOpen) return null;

  const restartMode = isRestart || tier === "RESTART";
  const warningNum = Math.min(5, Math.max(1, 6 - remainingWarnings));

  // Friendly description of detected violation kind
  const getKindDescription = (k: string) => {
    switch (k.toUpperCase()) {
      case "TAB_SWITCH":
        return "Browser tab switch or window minimize detected";
      case "WINDOW_BLUR":
        return "Application or window focus lost";
      case "FULLSCREEN_EXIT":
        return "Exited mandatory full-screen mode";
      case "NO_FACE":
      case "FACE_MISSING":
        return "No face visible in camera frame for > 3s";
      case "MULTIPLE_FACES":
        return "Multiple faces detected in camera frame";
      case "FACE_MISMATCH":
        return "Face does not match reference descriptor";
      case "LOOKING_AWAY":
        return "Face turned significantly away from screen";
      case "CAMERA_OFF":
        return "Webcam feed interrupted, covered, or turned off";
      case "COPY_PASTE":
        return "Clipboard copy/paste attempt blocked";
      case "DEV_TOOLS_KEY":
        return "Developer tools or restricted shortcut key pressed";
      default:
        return "Proctoring security policy incident";
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/85 backdrop-blur-md flex items-center justify-center p-4 select-none">
      <div
        className={`max-w-lg w-full bg-white rounded-3xl shadow-2xl border overflow-hidden animate-fadeIn ${
          restartMode
            ? "border-rose-600 ring-4 ring-rose-600/30"
            : warningNum >= 4
            ? "border-rose-400 ring-4 ring-rose-500/20"
            : "border-amber-400 ring-4 ring-amber-500/20"
        }`}
      >
        {/* Modal Banner */}
        <div
          className={`p-6 text-white ${
            restartMode
              ? "bg-rose-800"
              : warningNum >= 4
              ? "bg-rose-700"
              : "bg-amber-600"
          }`}
        >
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-white/15 flex items-center justify-center shrink-0">
              {restartMode ? (
                <RotateCcw className="w-7 h-7 text-white" />
              ) : warningNum >= 4 ? (
                <ShieldAlert className="w-7 h-7 text-white" />
              ) : (
                <AlertTriangle className="w-7 h-7 text-white" />
              )}
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider font-semibold text-white/80">
                {restartMode
                  ? "EXAM SECURITY ENFORCEMENT"
                  : "PROCTORING SECURITY ALERT"}
              </p>
              <h2 className="text-xl font-bold tracking-tight">
                {restartMode
                  ? "TEST RESTARTED"
                  : `WARNING ${warningNum} of 5`}
              </h2>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 sm:p-8 space-y-5">
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1.5">
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              Detected Event
            </p>
            <p className="text-sm font-bold text-slate-900">
              {getKindDescription(kind)}
            </p>
          </div>

          <div className="text-xs text-slate-700 leading-relaxed space-y-2">
            {restartMode ? (
              <p className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-900 font-medium">
                You have exceeded the maximum of 5 allowed warnings. Your exam has been <strong>restarted</strong>: the timer has reset to a fresh 60:00, previous answers have been cleared, and your questions have been re-shuffled to a new order.
              </p>
            ) : (
              <p>
                <strong>WARNING {warningNum} of 5:</strong> Tab switching is not allowed. If you switch tabs or violate proctoring rules more than 5 times, your test will be automatically restarted.
              </p>
            )}
            <p className="text-slate-500">
              Please maintain fullscreen focus, stay seated directly in front of the camera, and do not switch windows or use keyboard shortcuts.
            </p>
          </div>
        </div>

        {/* Footer / Action */}
        <div className="p-6 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
          <span className="text-xs text-slate-500">
            {countdown > 0 ? (
              <span className="font-mono font-medium text-amber-700">
                Modal locked for {countdown}s...
              </span>
            ) : (
              <span className="text-emerald-700 font-medium">Acknowledged</span>
            )}
          </span>

          <button
            onClick={() => {
              try {
                if (document.documentElement.requestFullscreen) {
                  document.documentElement.requestFullscreen().catch(() => {});
                }
              } catch {}
              onAcknowledge();
            }}
            disabled={countdown > 0}
            className={`px-6 py-2.5 rounded-xl text-xs font-semibold shadow-sm transition-all flex items-center gap-2 cursor-pointer ${
              countdown > 0
                ? "bg-slate-200 text-slate-400 cursor-not-allowed"
                : restartMode
                ? "bg-rose-700 hover:bg-rose-800 text-white"
                : "bg-brand-600 hover:bg-brand-700 text-white"
            }`}
          >
            {restartMode ? (
              <>
                <RotateCcw className="w-4 h-4 stroke-[2.5]" />
                <span>Resume Restarted Test</span>
              </>
            ) : (
              <>
                <Check className="w-4 h-4 stroke-[2.5]" />
                <span>I Understand, Resume Test</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
