import React, { useState, useEffect } from "react";
import { UserSession, CandidateStatus, ExamData } from "./types";
import { Navbar } from "./components/Navbar";
import { LoginPage } from "./components/LoginPage";
import { RulesConsentPage } from "./components/RulesConsentPage";
import { SystemCheckPage } from "./components/SystemCheckPage";
import { ExamScreen } from "./components/ExamScreen";
import { SubmissionSuccessPage } from "./components/SubmissionSuccessPage";
import { MonitorWall } from "./components/MonitorWall";
import { AdminConsole } from "./components/AdminConsole";
import { api } from "./services/api";
import { Language, getInitialLanguage, setStoredLanguage } from "./utils/language";

type AppStage = "LOGIN" | "RULES_CONSENT" | "SYSTEM_CHECK" | "EXAM" | "COMPLETED" | "STAFF";

export const App: React.FC = () => {
  const [session, setSession] = useState<UserSession | null>(null);
  const [stage, setStage] = useState<AppStage>("LOGIN");
  const [candidateStatus, setCandidateStatus] = useState<CandidateStatus | null>(null);
  const [examData, setExamData] = useState<ExamData | null>(null);
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);
  const [adminView, setAdminView] = useState<"WALL" | "CONSOLE">("WALL");
  const [loading, setLoading] = useState(true);
  const [language, setLanguage] = useState<Language>(getInitialLanguage());

  const handleLanguageChange = (lang: Language) => {
    setLanguage(lang);
    setStoredLanguage(lang);
  };

  // Restore session from localStorage on mount
  useEffect(() => {
    const token = localStorage.getItem("assess_token");
    const role = localStorage.getItem("assess_role") as any;
    const code = localStorage.getItem("assess_emp_code");
    const name = localStorage.getItem("assess_full_name");

    if (token && role && code && name) {
      const restoredSession: UserSession = {
        accessToken: token,
        role: role,
        employeeCode: code,
        fullName: name,
      };
      setSession(restoredSession);

      if (role === "MONITOR" || role === "ADMIN") {
        setStage("STAFF");
        setLoading(false);
      } else {
        // Fetch candidate status
        api.getStatus()
          .then((st) => {
            setCandidateStatus(st);
            if (st.status === "SUBMITTED" || st.status === "AUTO_SUBMITTED") {
              setStage("COMPLETED");
            } else if (!st.consentAt) {
              setStage("RULES_CONSENT");
            } else {
              setStage("SYSTEM_CHECK");
            }
          })
          .catch(() => {
            // Token expired or invalid
            api.logout();
            setSession(null);
            setStage("LOGIN");
          })
          .finally(() => setLoading(false));
      }
    } else {
      setLoading(false);
    }
  }, []);

  const handleLoginSuccess = async (user: UserSession) => {
    setSession(user);
    if (user.role === "MONITOR" || user.role === "ADMIN") {
      setStage("STAFF");
    } else {
      try {
        const st = await api.getStatus();
        setCandidateStatus(st);
        if (st.status === "SUBMITTED" || st.status === "AUTO_SUBMITTED") {
          setStage("COMPLETED");
        } else if (!st.consentAt) {
          setStage("RULES_CONSENT");
        } else {
          setStage("SYSTEM_CHECK");
        }
      } catch (e) {
        setStage("RULES_CONSENT");
      }
    }
  };

  const handleConsentGiven = () => {
    setStage("SYSTEM_CHECK");
  };

  const handleSystemCheckComplete = async (stream: MediaStream) => {
    setMediaStream(stream);
    try {
      const exam = await api.getExam();
      setExamData(exam);
      setStage("EXAM");
    } catch (err: any) {
      alert("Failed to start assessment: " + (err.message || "Unknown error"));
    }
  };

  const handleExamSubmitted = async () => {
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
    }
    try {
      const st = await api.getStatus();
      setCandidateStatus(st);
    } catch {}
    setStage("COMPLETED");
  };

  const handleLogout = () => {
    if (mediaStream) {
      mediaStream.getTracks().forEach((t) => t.stop());
    }
    api.logout();
    setSession(null);
    setCandidateStatus(null);
    setExamData(null);
    setStage("LOGIN");
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-3 border-brand-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Loading Assessment Portal...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      {stage !== "EXAM" && (
        <Navbar
          user={session}
          onLogout={session ? handleLogout : undefined}
          examTitle={examData?.assessmentTitle}
          language={language}
          onLanguageChange={handleLanguageChange}
        />
      )}

      {stage === "LOGIN" && <LoginPage onLoginSuccess={handleLoginSuccess} />}

      {stage === "RULES_CONSENT" && session && (
        <RulesConsentPage user={session} onConsentGiven={handleConsentGiven} />
      )}

      {stage === "SYSTEM_CHECK" && session && (
        <SystemCheckPage
          user={session}
          onSystemCheckComplete={handleSystemCheckComplete}
        />
      )}

      {stage === "EXAM" && session && examData && (
        <ExamScreen
          user={session}
          examData={examData}
          stream={mediaStream}
          onSubmitted={handleExamSubmitted}
          language={language}
          onLanguageChange={handleLanguageChange}
        />
      )}

      {stage === "COMPLETED" && session && (
        <SubmissionSuccessPage
          user={session}
          status={candidateStatus}
          onLogout={handleLogout}
        />
      )}

      {stage === "STAFF" && session && session.role === "MONITOR" && (
        <MonitorWall user={session} onLogout={handleLogout} />
      )}

      {stage === "STAFF" && session && session.role === "ADMIN" && (
        <div className="flex flex-col min-h-screen">
          <div className="bg-slate-900 border-b border-slate-800 text-white px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2.5">
              <span className="font-bold tracking-wider text-brand-400 font-mono">STAFF ACCESS</span>
              <span className="text-slate-500">•</span>
              <span className="text-slate-300">
                Logged in as <strong className="text-white">{session.fullName}</strong> ({session.role})
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setAdminView("WALL")}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer ${
                  adminView === "WALL"
                    ? "bg-brand-600 text-white font-semibold shadow-xs"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                📹 Live Camera Wall (Camera Moments)
              </button>
              <button
                onClick={() => setAdminView("CONSOLE")}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer ${
                  adminView === "CONSOLE"
                    ? "bg-brand-600 text-white font-semibold shadow-xs"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                📊 Admin Console & Results
              </button>
            </div>
          </div>
          {adminView === "WALL" ? (
            <MonitorWall user={session} onLogout={handleLogout} />
          ) : (
            <AdminConsole user={session} onLogout={handleLogout} />
          )}
        </div>
      )}
    </div>
  );
};
