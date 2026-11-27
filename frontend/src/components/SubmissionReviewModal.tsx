import React, { useState } from "react";
import { AlertCircle, CheckCircle2, Flag, HelpCircle, X, CheckSquare, Square } from "lucide-react";

interface SubmissionReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirmSubmit: () => void;
  totalQuestions: number;
  answeredCount: number;
  flaggedCount: number;
  remainingSeconds: number;
  loading: boolean;
}

export const SubmissionReviewModal: React.FC<SubmissionReviewModalProps> = ({
  isOpen,
  onClose,
  onConfirmSubmit,
  totalQuestions,
  answeredCount,
  flaggedCount,
  remainingSeconds,
  loading,
}) => {
  const [declared, setDeclared] = useState(true);

  if (!isOpen) return null;

  const unansweredCount = totalQuestions - answeredCount;
  const minutes = Math.floor(remainingSeconds / 60);
  const seconds = remainingSeconds % 60;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-200 overflow-hidden animate-fadeIn">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-brand-50 text-brand-600 flex items-center justify-center">
              <AlertCircle className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-slate-900 text-base">Submit Assessment?</h3>
          </div>
          <button
            onClick={onClose}
            disabled={loading}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          <p className="text-xs text-slate-500 leading-relaxed">
            Please review your progress before final submission. Once submitted, your answers are finalized and graded immediately. This action cannot be reversed.
          </p>

          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-100 text-center">
              <p className="text-xl font-bold text-emerald-700">{answeredCount}</p>
              <p className="text-[11px] text-emerald-600 font-medium">Answered</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-center">
              <p className="text-xl font-bold text-slate-700">{unansweredCount}</p>
              <p className="text-[11px] text-slate-500 font-medium">Unanswered</p>
            </div>
            <div className="p-3 rounded-xl bg-amber-50 border border-amber-100 text-center">
              <p className="text-xl font-bold text-amber-700">{flaggedCount}</p>
              <p className="text-[11px] text-amber-600 font-medium">Flagged</p>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-100 text-slate-700 text-xs flex items-center justify-between">
            <span className="font-medium">Time Remaining:</span>
            <span className="font-mono font-bold text-brand-700 text-sm">
              {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
            </span>
          </div>

          {unansweredCount > 0 && (
            <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <span>
                You still have {unansweredCount} unanswered questions. All unanswered questions score 0 marks.
              </span>
            </div>
          )}

          {/* Candidate Final Declaration (८. उमेदवाराची अंतिम घोषणा) */}
          <div className="p-3.5 rounded-xl bg-purple-50/70 border border-purple-200/90 text-xs space-y-2">
            <p className="font-semibold text-purple-950 leading-snug">
              ८. उमेदवाराची अंतिम घोषणा:
            </p>
            <p className="text-[11px] text-purple-900 leading-relaxed italic">
              "मी प्रमाणित करतो/करते की वरील सर्व माहिती खरी असून मी ही परीक्षा पूर्ण प्रामाणिकपणे दिली आहे."
            </p>
            <label className="flex items-center gap-2 cursor-pointer pt-1 select-none font-medium text-slate-800">
              <input
                type="checkbox"
                checked={declared}
                onChange={(e) => setDeclared(e.target.checked)}
                className="w-4 h-4 text-brand-600 rounded border-slate-300 focus:ring-brand-500 cursor-pointer"
              />
              <span className="text-xs font-semibold text-brand-900">
                होय, मी सहमत आहे (I Agree & Confirm)
              </span>
            </label>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-200 text-xs font-semibold transition-colors cursor-pointer"
          >
            Review Questions
          </button>
          <button
            onClick={onConfirmSubmit}
            disabled={loading || !declared}
            className="px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold shadow-sm transition-all flex items-center gap-2 cursor-pointer"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            ) : (
              <span>Confirm & Submit</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
