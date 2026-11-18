import React from "react";
import { ShieldCheck, LogOut } from "lucide-react";
import { UserSession } from "../types";

interface NavbarProps {
  user: UserSession | null;
  onLogout?: () => void;
  examTitle?: string;
}

export const Navbar: React.FC<NavbarProps> = ({ user, onLogout, examTitle }) => {
  return (
    <header className="h-16 border-b border-slate-200 bg-white/80 backdrop-blur-md sticky top-0 z-40 px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center text-white shadow-sm shadow-brand-500/30">
          <ShieldCheck className="w-6 h-6" />
        </div>
        <div>
          <h1 className="font-semibold text-slate-900 text-sm tracking-tight leading-none">
            {examTitle || "HR Team Assessment Portal"}
          </h1>
          <p className="text-xs text-slate-500 mt-1 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block animate-pulse"></span>
            Secure Online Proctoring Active
          </p>
        </div>
      </div>

      {user && (
        <div className="flex items-center gap-4">
          <div className="text-right hidden sm:block">
            <p className="text-xs font-semibold text-slate-800 leading-none">{user.fullName}</p>
            <p className="text-[11px] font-mono text-slate-500 mt-0.5">{user.employeeCode} • {user.role}</p>
          </div>
          {onLogout && (
            <button
              onClick={onLogout}
              className="p-2 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      )}
    </header>
  );
};
