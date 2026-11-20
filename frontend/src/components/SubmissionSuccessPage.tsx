import React from "react";
import { CheckCircle2, Award, Clock, ArrowRight } from "lucide-react";
import { CandidateStatus, UserSession } from "../types";

interface SubmissionSuccessPageProps {
  user: UserSession;
  status: CandidateStatus | null;
  onLogout: () => void;
}

export const SubmissionSuccessPage: React.FC<SubmissionSuccessPageProps> = ({
  user,
  status,
  onLogout,
}) => {
  const isPass = status?.result === "PASS" || (status?.score !== null && status?.score !== undefined && status.score >= 35);

  return (
    <div className="min-h-[85vh] flex items-center justify-center p-6">
      <div className="max-w-lg w-full bg-white rounded-3xl border border-slate-200 shadow-xl p-8 sm:p-10 text-center space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto shadow-md shadow-emerald-500/10">
          <CheckCircle2 className="w-10 h-10" />
        </div>

        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
            Assessment Completed
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Your assessment has been securely recorded and synced to Google Sheets.
          </p>
        </div>

        {/* Candidate Info Badge */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 text-left space-y-2 text-xs">
          <div className="flex justify-between py-1 border-b border-slate-200/60">
            <span className="text-slate-500">Candidate:</span>
            <span className="font-semibold text-slate-800">{user.fullName}</span>
          </div>
          <div className="flex justify-between py-1 border-b border-slate-200/60">
            <span className="text-slate-500">Employee Code:</span>
            <span className="font-mono font-semibold text-slate-800">{user.employeeCode}</span>
          </div>
          <div className="flex justify-between py-1 border-b border-slate-200/60">
            <span className="text-slate-500">Department:</span>
            <span className="font-semibold text-brand-700">{user.department || "HR"}</span>
          </div>
          <div className="flex justify-between py-1">
            <span className="text-slate-500">Proctoring Status:</span>
            <span className="font-semibold text-emerald-700">Audit Log Recorded</span>
          </div>
        </div>

        {/* Score & Detailed Analytics Card */}
        {status?.score !== null && status?.score !== undefined ? (
          <div className="p-5 rounded-2xl bg-white border border-slate-200 text-center space-y-4 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Exam Result</span>
              <span
                className={`px-3 py-1 rounded-full text-xs font-extrabold tracking-wide ${
                  isPass
                    ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                    : "bg-rose-100 text-rose-800 border border-rose-300"
                }`}
              >
                {isPass ? "PASS" : "FAIL"}
              </span>
            </div>

            <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Score</p>
              <p className="text-4xl font-extrabold text-slate-900 font-mono mt-1">
                {status.score} <span className="text-xl text-slate-400 font-normal">/ 100</span>
              </p>
              <p className="text-[11px] text-slate-500 mt-1">
                Pass Mark: 35 / 100 | Percentage: {status.percentage ?? status.score}%
              </p>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div className="p-2.5 bg-emerald-50 rounded-xl border border-emerald-100">
                <p className="text-emerald-700 font-bold text-lg">{status.correctCount ?? 0}</p>
                <p className="text-emerald-600 text-[10px] uppercase font-semibold">Correct</p>
              </div>
              <div className="p-2.5 bg-rose-50 rounded-xl border border-rose-100">
                <p className="text-rose-700 font-bold text-lg">{status.wrongCount ?? 0}</p>
                <p className="text-rose-600 text-[10px] uppercase font-semibold">Wrong</p>
              </div>
              <div className="p-2.5 bg-slate-100 rounded-xl border border-slate-200">
                <p className="text-slate-700 font-bold text-lg">{status.unansweredCount ?? 0}</p>
                <p className="text-slate-500 text-[10px] uppercase font-semibold">Unanswered</p>
              </div>
            </div>

            {status.timeTakenFormatted && (
              <div className="flex items-center justify-center gap-1.5 text-xs text-slate-500">
                <Clock className="w-3.5 h-3.5" />
                <span>Time Taken: <strong className="text-slate-700">{status.timeTakenFormatted}</strong></span>
              </div>
            )}
          </div>
        ) : (
          <div className="p-4 rounded-xl bg-slate-100 text-slate-600 text-xs leading-relaxed">
            Your exam answers have been securely synced. HR Talent Operations will review the final performance moderation.
          </div>
        )}

        <button
          onClick={onLogout}
          className="w-full py-3 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-medium text-xs shadow-md transition-colors cursor-pointer"
        >
          Close Session
        </button>
      </div>
    </div>
  );
};
