import React, { useState, useEffect } from "react";
import { AlertTriangle, ShieldAlert, RotateCcw, Check } from "lucide-react";

interface WarningModalProps {
  isOpen: boolean;
  tier: string; // "WARNING_1" | "WARNING_2" | "WARNING_3" | "FINAL_WARNING" | "RESTART"
  kind: string;
  message: string;
  remainingWarnings: number;
  warningNumber?: number;
  isRestart?: boolean;
  onAcknowledge: () => void;
}

export const WarningModal: React.FC<WarningModalProps> = ({
  isOpen,
  tier,
  kind,
  message,
  remainingWarnings,
  warningNumber,
  isRestart = false,
  onAcknowledge,
}) => {
  const [countdown, setCountdown] = useState(2);

  useEffect(() => {
    if (!isOpen) {
      setCountdown(2);
      return;
    }
    setCountdown(2);
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
  const warningNum = warningNumber ?? Math.min(5, Math.max(1, 5 - remainingWarnings));

  // Friendly description of detected violation kind
  const getKindDescription = (k: string) => {
    switch (k.toUpperCase()) {
      case "TAB_SWITCH":
        return "टॅब बदलणे किंवा विंडो मिनिमाईझ आढळले / Browser tab switch or window minimize detected";
      case "WINDOW_BLUR":
        return "विंडो किंवा ऍप्लिकेशन फोकस गमावले / Window focus lost (switched away)";
      case "FULLSCREEN_EXIT":
        return "फुलस्क्रीन मोडमधून बाहेर पडणे / Exited mandatory full-screen mode";
      case "NO_FACE":
      case "FACE_MISSING":
        return "कॅमेऱ्यामध्ये चेहरा दिसत नाही आहे / No face detected in camera frame (> 3s)";
      case "MULTIPLE_FACES":
        return "कॅमेऱ्यामध्ये एकापेक्षा जास्त चेहरे आढळले / Multiple faces detected in camera frame";
      case "FACE_MISMATCH":
        return "चेहरा जुळत नाही / Face does not match reference descriptor";
      case "LOOKING_AWAY":
        return "स्क्रीनवरून इतरत्र पाहणे आढळले / Face turned away from screen (> 5s)";
      case "CAMERA_OFF":
        return "कॅमेरा बंद किंवा कव्हर केलेला आढळला / Webcam feed interrupted or blocked";
      case "COPY_PASTE":
        return "कॉपी / पेस्ट करण्याचा प्रयत्न / Prohibited clipboard copy/paste attempt";
      case "DEV_TOOLS_KEY":
        return "प्रतिबंधित शॉर्टकट की / Restricted shortcut key pressed";
      default:
        return "परीक्षा सुरक्षा उल्लंघन / Proctoring security policy incident";
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
                  : `इशारा क्रमांक ${warningNum} / 5 (WARNING ${warningNum} of 5)`}
              </h2>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 sm:p-8 space-y-5">
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1.5">
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              नोंदवलेली घटना / Detected Incident
            </p>
            <p className="text-sm font-bold text-slate-900">
              {getKindDescription(kind)}
            </p>
          </div>

          <div className="text-xs text-slate-700 leading-relaxed space-y-3">
            {restartMode ? (
              <p className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-900 font-medium">
                तुम्ही कमाल 5 इशाऱ्यांची मर्यादा ओलांडली आहे. तुमची परीक्षा पुन्हा सुरू करण्यात आली आहे: टायमर 60:00 वर रीसेट झाला आहे आणि प्रश्न नव्याने क्रमवारी लावून दिले आहेत. तुमचे आधीचे उत्तर सुरक्षितपणे जतन केलेले आहेत.
              </p>
            ) : (
              <div className="space-y-2">
                {["TAB_SWITCH", "WINDOW_BLUR"].includes(kind.toUpperCase()) ? (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-900">
                    <p className="font-bold text-xs mb-1">
                      ⚠️ टॅब बदलणे पूर्णपणे निषिद्ध आहे (Tab Switch Strictly Prohibited)
                    </p>
                    <p className="text-[11px] leading-relaxed text-amber-800">
                      परीक्षा सुरू असताना इतर कोणत्याही ब्राऊझर टॅब, विंडो किंवा ऍप्लिकेशनमध्ये जाण्यास मनाई आहे. कृपया संपूर्ण वेळ याच स्क्रीनवर राहा.
                    </p>
                  </div>
                ) : ["NO_FACE", "FACE_MISSING", "CAMERA_OFF"].includes(kind.toUpperCase()) ? (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-900">
                    <p className="font-bold text-xs mb-1">
                      ⚠️ कॅमेऱ्यामध्ये चेहरा दिसत नाही आहे (Face Not Visible in Camera)
                    </p>
                    <p className="text-[11px] leading-relaxed text-rose-800">
                      तुमचा चेहरा वेबकॅमसमोर स्पष्ट दिसणे अनिवार्य आहे. कृपया थेट कॅमेऱ्यासमोर व्यवस्थित बसा आणि वेबकॅम कव्हर करू नका.
                    </p>
                  </div>
                ) : (
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-800">
                    <p className="font-bold text-xs mb-1">
                      ⚠️ परीक्षा सुरक्षा नियमांचे पालन करा (Adhere to Proctoring Rules)
                    </p>
                    <p className="text-[11px] leading-relaxed text-slate-700">
                      कृपया फुलस्क्रीन मोडमध्ये राहा, स्क्रीनवरून इतरत्र पाहू नका आणि कोणतेही शॉर्टकट वापरू नका.
                    </p>
                  </div>
                )}
                <p className="text-[11px] text-slate-500 font-medium pt-1">
                  शिल्लक इशारे / Remaining warnings before restart: <strong>{Math.max(0, 5 - warningNum)}</strong> of 5
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer / Action */}
        <div className="p-6 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
          <span className="text-xs text-slate-500">
            {countdown > 0 ? (
              <span className="font-mono font-medium text-amber-700">
                Wait {countdown}s to acknowledge...
              </span>
            ) : (
              <span className="text-emerald-700 font-medium">Please acknowledge</span>
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
                <span>परीक्षा पुन्हा सुरू करा / Resume Exam</span>
              </>
            ) : (
              <>
                <Check className="w-4 h-4 stroke-[2.5]" />
                <span>समजले, परीक्षा सुरू ठेवा / I Understand, Resume Test</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
