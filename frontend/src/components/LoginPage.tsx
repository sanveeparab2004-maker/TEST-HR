import React, { useState } from "react";
import { Shield, Lock, User, KeyRound, AlertCircle, ArrowRight, CheckCircle2 } from "lucide-react";
import { api } from "../services/api";
import { UserSession } from "../types";

interface LoginPageProps {
  onLoginSuccess: (session: UserSession) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [employeeCode, setEmployeeCode] = useState("");
  const [fullName, setFullName] = useState("");
  const [pin, setPin] = useState("");
  const [requiresPin, setRequiresPin] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCodeBlur = async () => {
    if (!employeeCode.trim()) return;
    try {
      const res = await api.lookup(employeeCode.trim());
      setRequiresPin(res.requires_pin);
    } catch {
      // Keep false on network blip
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
      const session = await api.login(employeeCode.trim(), fullName.trim(), pin.trim() || undefined);
      onLoginSuccess(session);
    } catch (err: any) {
      setError(err.message || "Details not found. Contact HR.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex bg-slate-50 text-slate-800">
      {/* Left Branded Panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-slate-900 relative p-12 flex-col justify-between overflow-hidden text-white">
        <div className="absolute inset-0 bg-gradient-to-br from-brand-900/60 via-slate-900 to-slate-950 z-0"></div>
        <div className="absolute top-0 right-0 -mr-20 -mt-20 w-96 h-96 rounded-full bg-brand-500/10 blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 -ml-20 -mb-20 w-96 h-96 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none"></div>

        <div className="relative z-10">
          <div className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-white/10 backdrop-blur-sm border border-white/10 text-xs font-medium text-brand-200">
            <Shield className="w-4 h-4 text-brand-400" />
            Official HR Assessment Environment
          </div>
        </div>

        <div className="relative z-10 max-w-md my-auto space-y-6">
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            HR Team Professional Assessment
          </h2>
          <p className="text-slate-300 text-sm leading-relaxed">
            Welcome to the secure assessment portal. This 60-minute test evaluates competencies across recruitment planning, sourcing, operations, MIS, and judgment.
          </p>

          <div className="space-y-3 pt-4 border-t border-slate-800">
            <div className="flex items-center gap-3 text-xs text-slate-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>50 Intermediate Multiple-Choice Questions (100 Marks total)</span>
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Deterministic scoring with zero negative marking</span>
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Continuous in-browser privacy-first proctoring verification</span>
            </div>
          </div>
        </div>

        <div className="relative z-10 text-xs text-slate-400">
          Strict single-device exam security enforced. Powered by Neon & Render.
        </div>
      </div>

      {/* Right Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md space-y-8">
          <div>
            <div className="w-12 h-12 rounded-xl bg-brand-600 flex items-center justify-center text-white mb-6 shadow-md shadow-brand-500/20 lg:hidden">
              <Shield className="w-6 h-6" />
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900">Sign in to begin</h2>
            <p className="text-sm text-slate-500 mt-2">
              Enter your assigned employee credentials to access the proctored assessment.
            </p>
          </div>

          {error && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-start gap-3">
              <AlertCircle className="w-5 h-5 shrink-0 text-rose-600 mt-0.5" />
              <div>
                <p className="font-medium">Authentication Failed</p>
                <p className="text-xs text-rose-600 mt-0.5">{error}</p>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                Employee Code
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <User className="w-5 h-5" />
                </div>
                <input
                  type="text"
                  required
                  placeholder="e.g. I-2607040 or E-2606026"
                  value={employeeCode}
                  onChange={(e) => setEmployeeCode(e.target.value)}
                  onBlur={handleCodeBlur}
                  className="w-full pl-11 pr-4 py-2.5 rounded-xl border border-slate-300 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 text-sm font-medium transition-all outline-none uppercase placeholder:normal-case"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                Full Name
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-5 h-5" />
                </div>
                <input
                  type="text"
                  required
                  placeholder="As registered in company roster"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full pl-11 pr-4 py-2.5 rounded-xl border border-slate-300 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 text-sm font-medium transition-all outline-none placeholder:text-slate-400"
                />
              </div>
            </div>

            {requiresPin && (
              <div className="animate-fadeIn">
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-xs font-semibold text-brand-700 uppercase tracking-wider">
                    Staff Security PIN
                  </label>
                  <span className="text-[11px] font-medium text-brand-600 bg-brand-50 px-2 py-0.5 rounded-full border border-brand-200">
                    Proctor / Admin Mode
                  </span>
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-brand-500">
                    <KeyRound className="w-5 h-5" />
                  </div>
                  <input
                    type="password"
                    required
                    placeholder="Enter 6-digit staff PIN"
                    value={pin}
                    onChange={(e) => setPin(e.target.value)}
                    className="w-full pl-11 pr-4 py-2.5 rounded-xl border border-brand-300 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 text-sm font-mono tracking-widest transition-all outline-none bg-brand-50/30"
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium text-sm shadow-md shadow-brand-600/25 transition-all disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <>
                  <span>Continue to Assessment</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="pt-6 border-t border-slate-200 text-center">
            <p className="text-xs text-slate-500">
              Need technical support or replacement device assistance? Contact <span className="font-semibold text-slate-700">hr-support@company.com</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
