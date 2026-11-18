import React, { useState } from "react";
import { ShieldCheck, Eye, Camera, Maximize, AlertTriangle, Clock, ArrowRight } from "lucide-react";
import { UserSession } from "../types";
import { api } from "../services/api";

interface RulesConsentPageProps {
  user: UserSession;
  onConsentGiven: () => void;
}

export const RulesConsentPage: React.FC<RulesConsentPageProps> = ({ user, onConsentGiven }) => {
  const [agreed, setAgreed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleProceed = async () => {
    if (!agreed) {
      setError("You must acknowledge and accept the proctoring guidelines to proceed.");
      return;
    }
    setLoading(true);
    try {
      await api.giveConsent();
      onConsentGiven();
    } catch (err: any) {
      setError(err.message || "Failed to record consent");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-10 px-6">
      {/* Step Indicator */}
      <div className="flex items-center justify-between mb-8 pb-4 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <span className="w-7 h-7 rounded-full bg-brand-600 text-white text-xs font-bold flex items-center justify-center">1</span>
          <span className="text-sm font-semibold text-slate-900">Rules & Consent</span>
        </div>
        <div className="w-12 h-0.5 bg-slate-200"></div>
        <div className="flex items-center gap-2 text-slate-400">
          <span className="w-7 h-7 rounded-full bg-slate-100 text-xs font-medium flex items-center justify-center">2</span>
          <span className="text-sm font-medium">System Check</span>
        </div>
        <div className="w-12 h-0.5 bg-slate-200"></div>
        <div className="flex items-center gap-2 text-slate-400">
          <span className="w-7 h-7 rounded-full bg-slate-100 text-xs font-medium flex items-center justify-center">3</span>
          <span className="text-sm font-medium">Assessment</span>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8 space-y-8">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Assessment Code of Conduct & Privacy Notice</h2>
          <p className="text-sm text-slate-500 mt-1">
            Candidate: <span className="font-semibold text-slate-800">{user.fullName}</span> ({user.employeeCode})
          </p>
        </div>

        {/* Highlight Banner */}
        <div className="p-4 rounded-xl bg-brand-50 border border-brand-100 flex items-start gap-3">
          <Clock className="w-5 h-5 text-brand-600 shrink-0 mt-0.5" />
          <div className="text-sm text-brand-900">
            <p className="font-semibold">Duration: 60 Minutes (Strict Server Clock)</p>
            <p className="text-xs text-brand-700 mt-0.5 leading-relaxed">
              Once you start, the 60-minute countdown runs on the server. Navigating away, closing the tab, or changing local laptop time does not pause the clock. If time expires, all saved answers are automatically submitted.
            </p>
          </div>
        </div>

        {/* 4 Pillars of Proctoring */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl border border-slate-200/80 bg-slate-50/50 space-y-2">
            <div className="flex items-center gap-2 text-brand-600 font-semibold text-sm">
              <Camera className="w-4 h-4 text-rose-600" />
              <span className="text-slate-900 font-bold">Compulsory Camera Monitoring</span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Keeping your camera open, active, and unobstructed is strictly compulsory for the full 60 minutes. The assessment content freezes immediately if your camera is disconnected or revoked.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-slate-200/80 bg-slate-50/50 space-y-2">
            <div className="flex items-center gap-2 text-brand-600 font-semibold text-sm">
              <Maximize className="w-4 h-4" />
              <span>Fullscreen & Tab Focus</span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              The test runs in compulsory fullscreen mode. Tab switching, window blurring, and exiting fullscreen trigger automated proctoring alerts.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-slate-200/80 bg-slate-50/50 space-y-2">
            <div className="flex items-center gap-2 text-brand-600 font-semibold text-sm">
              <Eye className="w-4 h-4" />
              <span>In-Browser AI Verification</span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Face presence and gaze alignment run client-side in your browser via lightweight WASM. No video frames leave your machine for AI analysis.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-slate-200/80 bg-slate-50/50 space-y-2">
            <div className="flex items-center gap-2 text-brand-600 font-semibold text-sm">
              <AlertTriangle className="w-4 h-4" />
              <span>Honest Warning System</span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              You receive up to 3 warnings followed by a Final Warning. The system will NEVER disqualify you automatically; human HR proctors review all flagged events.
            </p>
          </div>
        </div>

        {/* Privacy & Retention Details */}
        <div className="p-4 rounded-xl border border-slate-200 text-xs text-slate-600 space-y-1.5 bg-white">
          <p className="font-semibold text-slate-800">What is stored and data retention (DPDP Act Compliance):</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Only small timestamped violation snapshots (320px JPEG) are retained when security incidents occur.</li>
            <li>Stored data is visible exclusively to the assigned proctor and HR audit committee.</li>
            <li>All proctoring logs and snapshots are automatically purged after 90 days.</li>
          </ul>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium">
            {error}
          </div>
        )}

        {/* Consent Checkbox */}
        <div className="pt-2 border-t border-slate-200">
          <label className="flex items-start gap-3 cursor-pointer group select-none">
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => {
                setAgreed(e.target.checked);
                if (error) setError(null);
              }}
              className="mt-0.5 w-4 h-4 text-brand-600 rounded border-slate-300 focus:ring-brand-500 cursor-pointer"
            />
            <span className="text-xs text-slate-700 leading-relaxed">
              I have read, understood, and agree to the assessment guidelines and proctoring privacy terms. I consent to live camera monitoring, activity logging, and single-device enforcement during this 60-minute test.
            </span>
          </label>
        </div>

        {/* Action Button */}
        <div className="flex justify-end pt-2">
          <button
            onClick={handleProceed}
            disabled={!agreed || loading}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium text-sm shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            ) : (
              <>
                <span>Proceed to System Check</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
