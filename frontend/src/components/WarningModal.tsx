import React, { useState, useEffect } from "react";
import { AlertTriangle, ShieldAlert, Check } from "lucide-react";

interface WarningModalProps {
  isOpen: boolean;
  tier: string; // "WARNING_1" | "WARNING_2" | "WARNING_3" | "FINAL_WARNING"
  kind: string;
  message: string;
  remainingWarnings: number;
  onAcknowledge: () => void;
}

export const WarningModal: React.FC<WarningModalProps> = ({
  isOpen,
  tier,
  kind,
  message,
  remainingWarnings,
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

  const isFinalWarning = tier === "FINAL_WARNING";

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
        return "No face visible in camera frame";
      case "LOOKING_AWAY":
        return "Face turned significantly away from screen";
      case "CAMERA_OFF":
        return "Webcam feed interrupted or turned off";
      case "COPY_PASTE":
        return "Clipboard copy/paste attempt blocked";
      case "DEV_TOOLS_KEY":
        return "Developer tools or restricted shortcut key pressed";
      default:
        return "Proctoring security policy incident";
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 select-none">
      <div
        className={`max-w-lg w-full bg-white rounded-3xl shadow-2xl border overflow-hidden animate-fadeIn ${
          isFinalWarning ? "border-rose-400 ring-4 ring-rose-500/20" : "border-amber-300 ring-4 ring-amber-500/20"
        }`}
      >
        {/* Modal Banner */}
        <div
          className={`p-6 text-white ${
            isFinalWarning ? "bg-rose-700" : "bg-amber-600"
          }`}
        >
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-white/15 flex items-center justify-center shrink-0">
              {isFinalWarning ? (
                <ShieldAlert className="w-7 h-7 text-white" />
              ) : (
                <AlertTriangle className="w-7 h-7 text-white" />
              )}
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider font-semibold text-white/80">
                {isFinalWarning ? "CRITICAL PROCTORING NOTICE" : "PROCTORING SECURITY ALERT"}
              </p>
              <h2 className="text-xl font-bold tracking-tight">
                {isFinalWarning ? "FINAL WARNING" : `Warning (${4 - remainingWarnings}/3)`}
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

          <p className="text-xs text-slate-600 leading-relaxed">
            {isFinalWarning ? (
              <span className="font-medium text-slate-800">
                You have used all 3 initial warnings. This is your <strong>Final Warning</strong>. Your activity is being monitored and continuously reviewed by HR. You may continue the test, but all further incidents will be recorded on your proctoring log for post-exam committee review.
              </span>
            ) : (
              <span>
                {message} Please maintain active window focus, keep your camera connected, and face the screen.
              </span>
            )}
          </p>

          <div className="p-3.5 rounded-xl bg-slate-100 border border-slate-200 text-xs text-slate-600 space-y-1">
            <p className="font-semibold text-slate-800">Important Policy Reminder:</p>
            <p className="text-[11px] leading-relaxed">
              The automated system will not kick you out of the exam. The assessment clock continues running. Any penalty is a later human decision reviewed by HR.
            </p>
          </div>
        </div>

        {/* Footer / Action */}
        <div className="p-6 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
          <span className="text-xs text-slate-500">
            {countdown > 0 ? (
              <span className="font-mono font-medium text-amber-700">
                Button enabled in {countdown}s...
              </span>
            ) : (
              <span className="text-emerald-700 font-medium">Ready to acknowledge</span>
            )}
          </span>

          <button
            onClick={() => {
              // Re-enter fullscreen when acknowledging
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
                : isFinalWarning
                ? "bg-rose-600 hover:bg-rose-700 text-white"
                : "bg-brand-600 hover:bg-brand-700 text-white"
            }`}
          >
            <Check className="w-4 h-4 stroke-[2.5]" />
            <span>I Understand, Resume Test</span>
          </button>
        </div>
      </div>
    </div>
  );
};
