import React from "react";
import { ShieldCheck, LogOut, Globe } from "lucide-react";
import { UserSession } from "../types";
import { Language } from "../utils/language";

interface NavbarProps {
  user: UserSession | null;
  onLogout?: () => void;
  examTitle?: string;
  language?: Language;
  onLanguageChange?: (lang: Language) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  onLogout,
  examTitle,
  language,
  onLanguageChange,
}) => {
  return (
    <header className="h-16 border-b border-slate-200 bg-white/80 backdrop-blur-md sticky top-0 z-40 px-4 sm:px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center text-white shadow-sm shadow-brand-500/30">
          <ShieldCheck className="w-6 h-6" />
        </div>
        <div>
          <h1 className="font-semibold text-slate-900 text-sm tracking-tight leading-none">
            {examTitle || "CS Creative Solutions Assessment Portal"}
          </h1>
          <p className="text-xs text-slate-500 mt-1 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block animate-pulse"></span>
            Secure Online Proctoring Active
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 sm:gap-4">
        {/* Language Selection Selector (मराठी | English) */}
        {language && onLanguageChange && (
          <div className="flex items-center p-1 bg-slate-100 rounded-xl border border-slate-200">
            <div className="flex items-center gap-1 px-1.5 text-slate-500 hidden sm:flex">
              <Globe className="w-3.5 h-3.5" />
              <span className="text-[11px] font-semibold">भाषा / Lang:</span>
            </div>
            <button
              type="button"
              onClick={() => onLanguageChange("MR")}
              className={`px-2.5 py-1 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                language === "MR"
                  ? "bg-brand-600 text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              मराठी
            </button>
            <button
              type="button"
              onClick={() => onLanguageChange("EN")}
              className={`px-2.5 py-1 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                language === "EN"
                  ? "bg-brand-600 text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              English
            </button>
            <button
              type="button"
              onClick={() => onLanguageChange("BOTH")}
              className={`px-2 py-1 text-[11px] font-semibold rounded-lg transition-all cursor-pointer ${
                language === "BOTH"
                  ? "bg-brand-600 text-white shadow-xs"
                  : "text-slate-500 hover:text-slate-800"
              }`}
              title="दोन्ही भाषा (Both languages)"
            >
              Both
            </button>
          </div>
        )}

        {user && (
          <div className="flex items-center gap-3">
            <div className="text-right hidden md:block">
              <p className="text-xs font-semibold text-slate-800 leading-none">{user.fullName}</p>
              <p className="text-[11px] font-mono text-slate-500 mt-0.5">{user.employeeCode} • {user.role}</p>
            </div>
            {onLogout && (
              <button
                onClick={onLogout}
                className="p-2 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
                title="Logout"
              >
                <LogOut className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
      </div>
    </header>
  );
};
