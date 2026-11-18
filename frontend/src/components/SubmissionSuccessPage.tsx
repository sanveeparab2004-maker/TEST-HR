import React from "react";
import { CheckCircle2, ShieldCheck, ArrowRight } from "lucide-react";
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
  const showScore = status?.showScore;

  return (
    <div className="min-h-[80vh] flex items-center justify-center p-6">
      <div className="max-w-lg w-full bg-white rounded-3xl border border-slate-200 shadow-sm p-8 sm:p-10 text-center space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto shadow-md shadow-emerald-500/10">
          <CheckCircle2 className="w-10 h-10" />
        </div>

        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
            Assessment Completed
          </h2>
          <p className="text-sm text-slate-500 mt-2">
            Your assessment has been securely submitted and recorded.
          </p>
        </div>

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
            <span className="text-slate-500">Status:</span>
            <span className="font-semibold text-emerald-600">Submitted & Validated</span>
          </div>
          <div className="flex justify-between py-1">
            <span className="text-slate-500">Proctoring Log:</span>
            <span className="font-semibold text-slate-700">Integrity Verified</span>
          </div>
        </div>

        {showScore && status?.score !== null && status?.score !== undefined ? (
          <div className="p-5 rounded-2xl bg-brand-50 border border-brand-200 text-center space-y-2">
            <p className="text-xs font-semibold text-brand-700 uppercase tracking-wider">Your Score</p>
            <p className="text-4xl font-extrabold text-brand-800 font-mono">
              {status.score} <span className="text-xl text-brand-600 font-normal">/ 100</span>
            </p>
            <p className="text-xs text-brand-700 font-medium">
              Performance Band: <span className="font-bold">{status.band}</span>
            </p>
          </div>
        ) : (
          <div className="p-4 rounded-xl bg-slate-100 text-slate-600 text-xs leading-relaxed">
            Assessment results are withheld for administrative moderation. Your HR Talent Operations partner will release finalized performance bands following review.
          </div>
        )}

        <button
          onClick={onLogout}
          className="w-full py-3 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-medium text-xs shadow transition-colors cursor-pointer"
        >
          Close Session
        </button>
      </div>
    </div>
  );
};
