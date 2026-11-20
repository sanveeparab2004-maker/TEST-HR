import React, { useState } from "react";
import {
  Shield, Lock, User, KeyRound, AlertCircle, ArrowRight, CheckCircle2,
  Users, FileCheck, Briefcase, Building2, Clock, Sparkles
} from "lucide-react";
import { api } from "../services/api";
import { UserSession } from "../types";

interface LoginPageProps {
  onLoginSuccess: (session: UserSession) => void;
}

type DepartmentKey = "HR" | "CLAIM" | "TENDER" | "ADMIN";

interface DepartmentMeta {
  key: DepartmentKey;
  label: string;
  shortName: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  status: "ACTIVE" | "PENDING";
  statusText: string;
  color: string;
  badgeBg: string;
  questionsCount: string;
  highlights: string[];
}

const DEPARTMENTS: Record<DepartmentKey, DepartmentMeta> = {
  HR: {
    key: "HR",
    label: "HR Team Assessment",
    shortName: "HR",
    subtitle: "CS Creative Solutions • Recruitment, Sourcing, Operations, Excel MIS & Judgment",
    icon: Users,
    status: "ACTIVE",
    statusText: "Active • Live Test",
    color: "from-blue-600 to-indigo-700",
    badgeBg: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
    questionsCount: "100 Questions (100 Marks)",
    highlights: [
      "100 Multiple-Choice Questions (1 Mark each, 100 Marks Total)",
      "Strict 60-Minute Assessment Window with Automatic Timer",
      "Deterministic scoring with zero negative marking across all sections",
      "Continuous privacy-first proctoring with full-screen enforcement",
    ],
  },
  CLAIM: {
    key: "CLAIM",
    label: "Claims Team Assessment",
    shortName: "CLAIM",
    subtitle: "CS Creative Solutions • Claims Processing, Investigation, Auditing & Policy Compliance",
    icon: FileCheck,
    status: "PENDING",
    statusText: "Questionnaire Coming Soon",
    color: "from-amber-600 to-orange-700",
    badgeBg: "bg-amber-500/10 text-amber-300 border-amber-500/20",
    questionsCount: "100 Questions (100 Marks)",
    highlights: [
      "100 Multiple-Choice Questions (1 Mark each, 100 Marks Total)",
      "Claims Adjudication, Document Verification & Settlement Workflows",
      "Strict 60-Minute Timed Evaluation Window with Proctoring",
      "Questionnaire & candidate roster upload scheduled by HR",
    ],
  },
  TENDER: {
    key: "TENDER",
    label: "Tender Team Assessment",
    shortName: "TENDER",
    subtitle: "CS Creative Solutions • Bid Management, Tender Documentation, Evaluation & Vendor Relations",
    icon: Briefcase,
    status: "PENDING",
    statusText: "Questionnaire Coming Soon",
    color: "from-emerald-600 to-teal-700",
    badgeBg: "bg-teal-500/10 text-teal-300 border-teal-500/20",
    questionsCount: "100 Questions (100 Marks)",
    highlights: [
      "100 Multiple-Choice Questions (1 Mark each, 100 Marks Total)",
      "Tender Evaluation, Technical Bid Analysis & Statutory Guidelines",
      "Strict 60-Minute Timed Assessment Window with Proctoring",
      "Questionnaire & candidate roster upload scheduled by HR",
    ],
  },
  ADMIN: {
    key: "ADMIN",
    label: "Admin Operations Assessment",
    shortName: "ADMIN",
    subtitle: "CS Creative Solutions • Office Administration, Procurement, Facilities & Statutory Compliance",
    icon: Building2,
    status: "PENDING",
    statusText: "Questionnaire Coming Soon",
    color: "from-purple-600 to-indigo-800",
    badgeBg: "bg-purple-500/10 text-purple-300 border-purple-500/20",
    questionsCount: "100 Questions (100 Marks)",
    highlights: [
      "100 Multiple-Choice Questions (1 Mark each, 100 Marks Total)",
      "Administrative Workflows, Facility Management & Procurement",
      "Strict 60-Minute Timed Assessment Window with Proctoring",
      "Questionnaire & candidate roster upload scheduled by HR",
    ],
  },
};

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [selectedDept, setSelectedDept] = useState<DepartmentKey>("HR");
  const [employeeCode, setEmployeeCode] = useState("");
  const [fullName, setFullName] = useState("");
  const [pin, setPin] = useState("");
  const [requiresPin, setRequiresPin] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentMeta = DEPARTMENTS[selectedDept];

  const handleCodeBlur = async () => {
    if (!employeeCode.trim()) return;
    try {
      const res = await api.lookup(employeeCode.trim());
      setRequiresPin(res.requires_pin);
    } catch {
      setRequiresPin(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!employeeCode.trim() || !fullName.trim()) {
      setError("Please enter both your Employee Code and Full Name.");
      return;
    }

    if (requiresPin && !pin.trim()) {
      setError("PIN is required for Staff access.");
      return;
    }

    setLoading(true);
    try {
      const session = await api.login(
        employeeCode.trim(),
        fullName.trim(),
        pin.trim() || undefined,
        selectedDept
      );
      onLoginSuccess(session);
    } catch (err: any) {
      setError(err.message || "Authentication failed. Please verify credentials or contact HR.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex bg-slate-50 text-slate-800">
      {/* Left Branded Panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-slate-900 relative p-12 flex-col justify-between overflow-hidden text-white transition-all duration-500">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 z-0"></div>
        <div className="absolute top-0 right-0 -mr-20 -mt-20 w-96 h-96 rounded-full bg-brand-500/10 blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 -ml-20 -mb-20 w-96 h-96 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none"></div>

        {/* Top Badges */}
        <div className="relative z-10 flex items-center justify-between">
          <div className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-white/10 backdrop-blur-sm border border-white/10 text-xs font-medium text-brand-200">
            <Shield className="w-4 h-4 text-brand-400" />
            CS Creative Solutions Assessment Portal
          </div>
          <span className={`px-2.5 py-1 rounded-full text-[11px] font-semibold border ${currentMeta.badgeBg} flex items-center gap-1.5`}>
            {currentMeta.status === "ACTIVE" && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>}
            {currentMeta.statusText}
          </span>
        </div>

        {/* Middle Department Information */}
        <div className="relative z-10 max-w-lg my-auto space-y-6">
          <div className="space-y-2">
            <span className="text-xs uppercase tracking-widest text-brand-400 font-bold">
              CS Creative Solutions • {currentMeta.shortName} Track
            </span>
            <h2 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
              {currentMeta.label}
            </h2>
            <p className="text-slate-300 text-sm leading-relaxed">
              {currentMeta.subtitle}
            </p>
          </div>

          <div className="space-y-3 pt-4 border-t border-slate-800">
            {currentMeta.highlights.map((highlight, idx) => (
              <div key={idx} className="flex items-start gap-3 text-xs text-slate-300 leading-snug">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span>{highlight}</span>
              </div>
            ))}
          </div>

          <div className="pt-2 flex items-center gap-4 text-xs font-mono text-slate-400">
            <div className="flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-slate-500" />
              <span>Duration: 60 Minutes</span>
            </div>
            <span>•</span>
            <div>{currentMeta.questionsCount}</div>
          </div>
        </div>

        <div className="relative z-10 text-xs text-slate-400 flex items-center justify-between border-t border-slate-800/80 pt-4">
          <span>Continuous AI & Proctor Security Verification</span>
          <span className="font-mono text-slate-500">v1.2.0 • Standalone Portal</span>
        </div>
      </div>

      {/* Right Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-12 overflow-y-auto">
        <div className="w-full max-w-md space-y-6 py-6">
          <div>
            <div className="w-12 h-12 rounded-xl bg-brand-600 flex items-center justify-center text-white mb-4 shadow-md shadow-brand-500/20 lg:hidden">
              <Shield className="w-6 h-6" />
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900">Sign In to Assessment</h2>
            <p className="text-xs text-slate-500 mt-1">
              Select your department track and enter your authorized credentials.
            </p>
          </div>

          {/* Department Track Selector Tabs */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Select Department Track
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {(Object.keys(DEPARTMENTS) as DepartmentKey[]).map((key) => {
                const dept = DEPARTMENTS[key];
                const Icon = dept.icon;
                const isSelected = selectedDept === key;

                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => {
                      setSelectedDept(key);
                      setError(null);
                    }}
                    className={`p-2.5 rounded-xl border text-left transition-all relative flex flex-col justify-between ${
                      isSelected
                        ? "border-brand-600 bg-brand-50/70 shadow-sm ring-2 ring-brand-500/20"
                        : "border-slate-200 bg-white hover:bg-slate-50 text-slate-600"
                    }`}
                  >
                    <div className="flex items-center justify-between w-full mb-1">
                      <Icon className={`w-4 h-4 ${isSelected ? "text-brand-600" : "text-slate-400"}`} />
                      {dept.status === "ACTIVE" ? (
                        <span className="w-2 h-2 rounded-full bg-emerald-500" title="Active"></span>
                      ) : (
                        <span className="text-[9px] font-semibold text-slate-400">Soon</span>
                      )}
                    </div>
                    <span className={`text-xs font-bold ${isSelected ? "text-brand-900" : "text-slate-800"}`}>
                      {dept.shortName}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Department Notice Banner for Non-HR */}
          {selectedDept !== "HR" && (
            <div className="p-3.5 rounded-xl bg-amber-50/90 border border-amber-200 text-amber-800 text-xs space-y-1 animate-fadeIn">
              <div className="flex items-center gap-2 font-semibold">
                <Sparkles className="w-4 h-4 text-amber-600 shrink-0" />
                <span>{currentMeta.label} Section</span>
              </div>
              <p className="text-[11px] leading-relaxed text-amber-700">
                The question bank and candidate roster for the <strong>{currentMeta.shortName}</strong> department are scheduled for upload. HR candidates must switch to the <strong>HR</strong> section.
              </p>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-start gap-3 animate-fadeIn">
              <AlertCircle className="w-5 h-5 shrink-0 text-rose-600 mt-0.5" />
              <div>
                <p className="font-semibold text-xs">Authentication Alert</p>
                <p className="text-xs text-rose-600 mt-0.5">{error}</p>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Employee Code
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <User className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  required
                  placeholder="e.g. I-2607040 or E-2606026"
                  value={employeeCode}
                  onChange={(e) => setEmployeeCode(e.target.value)}
                  onBlur={handleCodeBlur}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-300 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 text-sm font-medium transition-all outline-none uppercase placeholder:normal-case placeholder:text-slate-400"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Full Name
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  required
                  placeholder="As registered in company roster"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-300 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 text-sm font-medium transition-all outline-none placeholder:text-slate-400"
                />
              </div>
            </div>

            {requiresPin && (
              <div className="animate-fadeIn">
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-brand-700 uppercase tracking-wider">
                    Staff Security PIN
                  </label>
                  <span className="text-[10px] font-medium text-brand-600 bg-brand-50 px-2 py-0.5 rounded-full border border-brand-200">
                    Proctor / Admin Mode
                  </span>
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-brand-500">
                    <KeyRound className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    required
                    placeholder="Enter 6-digit staff PIN"
                    value={pin}
                    onChange={(e) => setPin(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-brand-300 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 text-sm font-mono tracking-widest transition-all outline-none bg-brand-50/30"
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm shadow-md shadow-brand-600/25 transition-all disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <>
                  <span>Begin {currentMeta.shortName} Assessment</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick Info & Support footer */}
          <div className="pt-4 border-t border-slate-200 text-center space-y-1 text-xs text-slate-500">
            <p>
              Proctoring Lead / Staff Admin: <span className="font-mono font-medium text-slate-700">E-2606026</span>
            </p>
            <p className="text-[11px] text-slate-400">
              Need technical or proctoring support? Contact <span className="font-semibold text-slate-600">hr-support@company.com</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
