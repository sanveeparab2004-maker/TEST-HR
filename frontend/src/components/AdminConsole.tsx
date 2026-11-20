import React, { useState, useEffect } from "react";
import {
  Users, BarChart3, BookOpen, Settings, Download, Search,
  CheckCircle2, XCircle, AlertTriangle, FileSpreadsheet, FileText,
  Sparkles, RefreshCw, KeyRound, Trash2, ArrowUpDown, ChevronRight, X, ExternalLink, RotateCcw, Upload
} from "lucide-react";
import { UserSession } from "../types";

interface ResultRow {
  attempt_id: number | null;
  employee_code: string;
  full_name: string;
  department: string | null;
  status: string;
  score: number | null;
  percentage: number | null;
  band: string | null;
  warning_count: number;
  violation_count: number;
  integrity_status: string;
  time_taken_seconds: number | null;
  started_at: string | null;
  submitted_at: string | null;
}

interface AdminDashboardStats {
  assessment_title: string;
  assessment_status: string;
  total_candidates: number;
  submitted_count: number;
  in_progress_count: number;
  not_started_count: number;
  band_distribution: Record<string, number>;
  section_averages: Record<string, number>;
}

interface AdminConsoleProps {
  user: UserSession;
  onLogout: () => void;
}

export const AdminConsole: React.FC<AdminConsoleProps> = ({ user, onLogout }) => {
  const [activeTab, setActiveTab] = useState<"results" | "questions" | "controls">("results");
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);
  const [results, setResults] = useState<ResultRow[]>([]);
  const [questionBank, setQuestionBank] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Search & Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [deptFilter, setDeptFilter] = useState("ALL");

  // Candidate Drill-Down Drawer
  const [selectedAttemptId, setSelectedAttemptId] = useState<number | null>(null);
  const [candidateDetails, setCandidateDetails] = useState<any | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [generatingAi, setGeneratingAi] = useState(false);

  // Device lock release form
  const [releaseEmpCode, setReleaseEmpCode] = useState("");
  const [releaseReason, setReleaseReason] = useState("");
  const [releaseMessage, setReleaseMessage] = useState<string | null>(null);

  // Operations
  const [syncingSheet, setSyncingSheet] = useState(false);
  const [sheetSyncMessage, setSheetSyncMessage] = useState<string | null>(null);
  const [reconcileReport, setReconcileReport] = useState<any | null>(null);
  const [uploadingQuestions, setUploadingQuestions] = useState(false);
  const [questionUploadMessage, setQuestionUploadMessage] = useState<string | null>(null);
  const [importDepartment, setImportDepartment] = useState("HR");

  // Retention purge
  const [purgeDays, setPurgeDays] = useState(90);
  const [purgeMessage, setPurgeMessage] = useState<string | null>(null);

  const GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/184qGjXRADe6RLzAlBy3LGk78xzkUa8GXeqkBOzWvkWI";

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${localStorage.getItem("assess_token") || ""}` };
      const [dashRes, resultsRes] = await Promise.all([
        fetch("/api/admin/dashboard", { headers }),
        fetch("/api/admin/results", { headers }),
      ]);

      if (dashRes.ok) setStats(await dashRes.json());
      if (resultsRes.ok) setResults(await resultsRes.json());
    } catch {} finally {
      setLoading(false);
    }
  };

  const fetchQuestionBank = async () => {
    try {
      const res = await fetch("/api/admin/questions", {
        headers: { Authorization: `Bearer ${localStorage.getItem("assess_token") || ""}` },
      });
      if (res.ok) setQuestionBank(await res.json());
    } catch {}
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  useEffect(() => {
    if (activeTab === "questions" && questionBank.length === 0) {
      fetchQuestionBank();
    }
  }, [activeTab]);

  const handleOpenCandidate = async (attemptId: number) => {
    setSelectedAttemptId(attemptId);
    setLoadingDetails(true);
    try {
      const res = await fetch(`/api/admin/candidate/${attemptId}/details`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("assess_token") || ""}` },
      });
      if (res.ok) setCandidateDetails(await res.json());
    } catch {} finally {
      setLoadingDetails(false);
    }
  };

  const handleGenerateAiSummary = async () => {
    if (!selectedAttemptId) return;
    setGeneratingAi(true);
    try {
      const res = await fetch(`/api/admin/candidate/${selectedAttemptId}/ai-summary`, {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("assess_token") || ""}` },
      });
      if (res.ok) {
        const aiData = await res.json();
        setCandidateDetails((prev: any) => ({ ...prev, ai_summary: aiData }));
      }
    } catch {} finally {
      setGeneratingAi(false);
    }
  };

  const handleResyncToSheet = async () => {
    setSyncingSheet(true);
    setSheetSyncMessage("Syncing all completed attempts to Google Sheet...");
    try {
      const res = await fetch("/api/admin/resync-sheet", {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("assess_token") || ""}` },
      });
      const data = await res.json();
      setSheetSyncMessage(data.message || `Re-sync finished: synced ${data.synced_count} records.`);
    } catch {
      setSheetSyncMessage("Failed to connect to Google Sheets re-sync endpoint.");
    } finally {
      setSyncingSheet(false);
    }
  };

  const handleRunReconcile = async () => {
    try {
      const res = await fetch("/api/admin/reconcile", {
        headers: { Authorization: `Bearer ${localStorage.getItem("assess_token") || ""}` },
      });
      if (res.ok) {
        setReconcileReport(await res.json());
      } else {
        alert("Reconciliation check failed.");
      }
    } catch {
      alert("Network error running reconciliation.");
    }
  };

  const handleUploadQuestionPaper = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingQuestions(true);
    setQuestionUploadMessage(null);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("department", importDepartment);

    try {
      const res = await fetch("/api/admin/questions/import", {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("assess_token") || ""}` },
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setQuestionUploadMessage(`Successfully imported ${data.imported_count} questions for department ${data.department}! Total marks: ${data.total_marks}`);
        fetchQuestionBank();
      } else {
        setQuestionUploadMessage(`Import rejected: ${data.detail || "Validation error"}`);
      }
    } catch {
      setQuestionUploadMessage("Network error during file upload.");
    } finally {
      setUploadingQuestions(false);
      e.target.value = "";
    }
  };

  const handleReleaseDeviceLock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!releaseEmpCode.trim()) return;
    try {
      const res = await fetch("/api/admin/release-device-lock", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("assess_token") || ""}`,
        },
        body: JSON.stringify({
          employee_code: releaseEmpCode.trim(),
          reason: releaseReason.trim() || "Admin manual reset",
        }),
      });
      const data = await res.json();
      setReleaseMessage(data.message || data.detail);
      setReleaseEmpCode("");
      setReleaseReason("");
      fetchDashboardData();
    } catch {
      setReleaseMessage("Failed to release lock.");
    }
  };

  const handleResetCandidate = async (employeeCode: string, fullName: string) => {
    if (!window.confirm(`Are you sure you want to reset all attempt and device lock data for ${fullName} (${employeeCode})? This will allow them to start fresh from question 1.`)) {
      return;
    }
    try {
      const res = await fetch(`/api/admin/candidate/${employeeCode}/reset`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("assess_token") || ""}`,
        },
      });
      if (res.ok) {
        alert(`Candidate ${fullName} has been reset. They can now log in fresh.`);
        fetchDashboardData();
      } else {
        alert("Failed to reset candidate attempt.");
      }
    } catch {
      alert("Network error resetting candidate.");
    }
  };

  const handleResetAllAttempts = async () => {
    if (!window.confirm("CAUTION: Are you sure you want to wipe ALL test attempts? This resets all candidates back to unattempted state.")) {
      return;
    }
    try {
      const res = await fetch("/api/admin/reset-all-attempts", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("assess_token") || ""}`,
        },
      });
      if (res.ok) {
        alert("All candidate attempts have been reset successfully.");
        fetchDashboardData();
      } else {
        alert("Failed to reset attempts.");
      }
    } catch {
      alert("Network error resetting attempts.");
    }
  };

  const handlePurgeRetention = async () => {
    if (!window.confirm(`Are you sure you want to permanently purge proctoring logs older than ${purgeDays} days?`)) return;
    try {
      const res = await fetch(`/api/admin/purge-retention?days=${purgeDays}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("assess_token") || ""}` },
      });
      const data = await res.json();
      setPurgeMessage(data.message || "Purge executed.");
    } catch {
      setPurgeMessage("Error during purge.");
    }
  };

  const filteredResults = results.filter((r) => {
    const matchesSearch =
      r.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.employee_code.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "ALL" || r.status === statusFilter;
    const matchesDept = deptFilter === "ALL" || (r.department && r.department.toUpperCase().includes(deptFilter));
    return matchesSearch && matchesStatus && matchesDept;
  });

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Top Admin Header */}
      <header className="h-16 border-b border-slate-200 bg-white sticky top-0 z-30 px-6 sm:px-8 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-slate-900 flex items-center justify-center text-white">
            <BarChart3 className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <span>Admin & Results Dashboard</span>
              <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-[10px] font-mono border border-slate-200">
                ADMIN
              </span>
            </h1>
            <p className="text-xs text-slate-500">
              Operations Lead: <span className="text-slate-800 font-semibold">{user.fullName}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Live Google Sheet Link */}
          <a
            href={GOOGLE_SHEET_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 text-xs font-semibold transition-colors cursor-pointer"
            title="Open Live Master Google Sheet"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
            <span className="hidden md:inline">Open Google Sheet</span>
            <ExternalLink className="w-3.5 h-3.5 text-emerald-500" />
          </a>

          {/* Re-sync Button */}
          <button
            onClick={handleResyncToSheet}
            disabled={syncingSheet}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-800 border border-indigo-200 text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50"
            title="Re-sync all DB results to Google Sheet"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-indigo-600 ${syncingSheet ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">{syncingSheet ? "Syncing..." : "Re-sync Sheet"}</span>
          </button>

          {/* Multi-tab Comprehensive Excel Final Export */}
          <a
            href="/api/admin/finalize"
            download
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <Download className="w-4 h-4 text-emerald-400" />
            <span className="hidden sm:inline">Finalize & Export</span>
          </a>

          <button
            onClick={onLogout}
            className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition-colors"
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* Sync Status Toast Banner */}
      {sheetSyncMessage && (
        <div className="bg-indigo-600 text-white text-xs px-6 py-2 flex items-center justify-between">
          <span>{sheetSyncMessage}</span>
          <button onClick={() => setSheetSyncMessage(null)} className="text-white/80 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="border-b border-slate-200 bg-white px-6 sm:px-8">
        <div className="flex items-center gap-6 text-xs font-semibold">
          <button
            onClick={() => setActiveTab("results")}
            className={`py-3.5 border-b-2 flex items-center gap-2 transition-all cursor-pointer ${
              activeTab === "results"
                ? "border-brand-600 text-brand-700"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <Users className="w-4 h-4" />
            <span>Results & Analytics</span>
          </button>

          <button
            onClick={() => setActiveTab("questions")}
            className={`py-3.5 border-b-2 flex items-center gap-2 transition-all cursor-pointer ${
              activeTab === "questions"
                ? "border-brand-600 text-brand-700"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>Question Bank & Import</span>
          </button>

          <button
            onClick={() => setActiveTab("controls")}
            className={`py-3.5 border-b-2 flex items-center gap-2 transition-all cursor-pointer ${
              activeTab === "controls"
                ? "border-brand-600 text-brand-700"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <Settings className="w-4 h-4" />
            <span>Audit & Operational Controls</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 p-6 sm:p-8 max-w-7xl mx-auto w-full">
        {activeTab === "results" && (
          <div className="space-y-6">
            {/* KPI Cards */}
            {stats && (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Candidates</p>
                  <p className="text-3xl font-extrabold text-slate-900 font-mono mt-1">{stats.total_candidates}</p>
                  <p className="text-[11px] text-slate-400 mt-1">Official roster</p>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
                  <p className="text-xs font-medium text-emerald-600 uppercase tracking-wider">Completed (Submitted)</p>
                  <p className="text-3xl font-extrabold text-emerald-600 font-mono mt-1">{stats.submitted_count}</p>
                  <p className="text-[11px] text-slate-400 mt-1">Pass Mark: 35 / 100</p>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
                  <p className="text-xs font-medium text-amber-600 uppercase tracking-wider">Active In-Progress</p>
                  <p className="text-3xl font-extrabold text-amber-600 font-mono mt-1">{stats.in_progress_count}</p>
                  <p className="text-[11px] text-slate-400 mt-1">Live in assessment room</p>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Not Started</p>
                  <p className="text-3xl font-extrabold text-slate-600 font-mono mt-1">{stats.not_started_count}</p>
                  <p className="text-[11px] text-slate-400 mt-1">Single attempt permitted</p>
                </div>
              </div>
            )}

            {/* Results Table, Search, and Department Filter */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="p-4 sm:p-6 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4">
                <div className="relative w-full sm:w-72">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                  <input
                    type="text"
                    placeholder="Search candidate name or code..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs focus:bg-white focus:border-brand-500 outline-none"
                  />
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  {/* Department Filter */}
                  <select
                    value={deptFilter}
                    onChange={(e) => setDeptFilter(e.target.value)}
                    className="px-3 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs font-medium text-slate-700 outline-none cursor-pointer"
                  >
                    <option value="ALL">All Departments</option>
                    <option value="HR">HR Department</option>
                    <option value="CLAIM">Claim Department</option>
                    <option value="TENDER">Tender Department</option>
                    <option value="ADMIN">Admin Department</option>
                  </select>

                  {/* Status Filter */}
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="px-3 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs font-medium text-slate-700 outline-none cursor-pointer"
                  >
                    <option value="ALL">All Statuses</option>
                    <option value="SUBMITTED">Completed</option>
                    <option value="IN_PROGRESS">In Progress</option>
                    <option value="NOT_STARTED">Not Started</option>
                  </select>

                  <button
                    onClick={fetchDashboardData}
                    className="p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors cursor-pointer"
                    title="Refresh Table"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50/80 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-200">
                      <th className="py-3.5 px-4">Candidate</th>
                      <th className="py-3.5 px-3">Department</th>
                      <th className="py-3.5 px-3">Status</th>
                      <th className="py-3.5 px-3 text-center">Score (/100)</th>
                      <th className="py-3.5 px-3 text-center">Result</th>
                      <th className="py-3.5 px-3 text-center">Violations</th>
                      <th className="py-3.5 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {loading ? (
                      <tr>
                        <td colSpan={7} className="text-center py-12 text-slate-400">
                          Loading candidates and results...
                        </td>
                      </tr>
                    ) : filteredResults.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="text-center py-12 text-slate-400">
                          No candidate records found matching filters.
                        </td>
                      </tr>
                    ) : (
                      filteredResults.map((r) => {
                        const isPass = r.score !== null && r.score >= 35;
                        return (
                          <tr key={r.employee_code} className="hover:bg-slate-50/60 transition-colors">
                            <td className="py-3.5 px-4">
                              <p className="font-semibold text-slate-900">{r.full_name}</p>
                              <p className="text-[11px] text-slate-400 font-mono">{r.employee_code}</p>
                            </td>
                            <td className="py-3.5 px-3 text-slate-700 font-medium">
                              {r.department || "HR"}
                            </td>
                            <td className="py-3.5 px-3">
                              {r.status === "SUBMITTED" ? (
                                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 font-medium text-[11px] border border-emerald-200">
                                  <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                                  <span>Completed</span>
                                </span>
                              ) : r.status === "IN_PROGRESS" ? (
                                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 font-medium text-[11px] border border-amber-200">
                                  <RefreshCw className="w-3 h-3 text-amber-500 animate-spin" />
                                  <span>In Progress</span>
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 font-medium text-[11px]">
                                  <span>Not Started</span>
                                </span>
                              )}
                            </td>
                            <td className="py-3.5 px-3 text-center font-mono font-bold text-slate-800">
                              {r.score !== null ? `${r.score}` : "—"}
                            </td>
                            <td className="py-3.5 px-3 text-center">
                              {r.score !== null ? (
                                <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${
                                  isPass ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
                                }`}>
                                  {isPass ? "PASS" : "FAIL"}
                                </span>
                              ) : (
                                <span className="text-slate-400">—</span>
                              )}
                            </td>
                            <td className="py-3.5 px-3 text-center">
                              {r.violation_count > 0 ? (
                                <span className="inline-flex items-center gap-1 text-amber-700 font-medium">
                                  <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                                  <span>{r.violation_count}</span>
                                </span>
                              ) : (
                                <span className="text-slate-400">0</span>
                              )}
                            </td>
                            <td className="py-3.5 px-4 text-right space-x-2">
                              {r.attempt_id && (
                                <button
                                  onClick={() => handleOpenCandidate(r.attempt_id!)}
                                  className="px-2.5 py-1 rounded-lg bg-brand-50 hover:bg-brand-100 text-brand-700 text-xs font-semibold cursor-pointer"
                                >
                                  Review
                                </button>
                              )}
                              <button
                                onClick={() => handleResetCandidate(r.employee_code, r.full_name)}
                                className="px-2 py-1 rounded-lg bg-slate-100 hover:bg-rose-50 text-slate-600 hover:text-rose-700 text-xs font-medium cursor-pointer"
                                title="Reset candidate attempt so they can restart fresh"
                              >
                                Reset
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Question Bank & Department Import Tab */}
        {activeTab === "questions" && (
          <div className="space-y-6">
            {/* Import Question Bank Card */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Import Department Question Paper</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Upload a CSV or Excel file with question_id, department, question_text, option_a..d, correct_option, marks (Total must equal 100).
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <a
                    href="/api/admin/questions/template"
                    download
                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download CSV Template</span>
                  </a>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-wrap items-center gap-4">
                <div>
                  <label className="text-xs font-semibold text-slate-600 block mb-1">Target Department:</label>
                  <select
                    value={importDepartment}
                    onChange={(e) => setImportDepartment(e.target.value)}
                    className="p-2 rounded-lg bg-white border border-slate-300 text-xs font-medium outline-none"
                  >
                    <option value="HR">HR Department</option>
                    <option value="CLAIM">Claim Department</option>
                    <option value="TENDER">Tender Department</option>
                    <option value="ADMIN">Admin Department</option>
                  </select>
                </div>

                <div className="flex-1">
                  <label className="text-xs font-semibold text-slate-600 block mb-1">Choose Question Paper File (.csv or .xlsx):</label>
                  <input
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    onChange={handleUploadQuestionPaper}
                    disabled={uploadingQuestions}
                    className="text-xs text-slate-600 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-brand-600 file:text-white hover:file:bg-brand-700 cursor-pointer"
                  />
                </div>
              </div>

              {questionUploadMessage && (
                <div className="p-3 bg-slate-100 rounded-xl text-xs font-semibold text-slate-800 border border-slate-200">
                  {questionUploadMessage}
                </div>
              )}
            </div>

            {/* Questions Table */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="p-4 border-b border-slate-200 flex justify-between items-center">
                <h3 className="font-bold text-xs text-slate-900 uppercase tracking-wider">
                  Question Bank Roster ({questionBank.length} Loaded Questions)
                </h3>
              </div>
              <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="sticky top-0 bg-slate-50 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4">#</th>
                      <th className="py-3 px-3">Dept</th>
                      <th className="py-3 px-4">Question Text</th>
                      <th className="py-3 px-3">Correct Option</th>
                      <th className="py-3 px-3 text-center">Marks</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {questionBank.map((q, idx) => (
                      <tr key={q.id || idx} className="hover:bg-slate-50/50">
                        <td className="py-3 px-4 font-mono text-slate-400 font-semibold">{idx + 1}</td>
                        <td className="py-3 px-3 font-semibold text-brand-700">{q.department || "HR"}</td>
                        <td className="py-3 px-4 text-slate-800 max-w-md">{q.stem}</td>
                        <td className="py-3 px-3">
                          <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold">
                            {q.correct_label || "A"}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-center font-mono font-bold text-slate-700">{q.marks || 1}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Operational Controls & Audit Tab */}
        {activeTab === "controls" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Google Sheets Sync & Reconciliation */}
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
                <div className="flex items-center gap-2">
                  <FileSpreadsheet className="w-5 h-5 text-emerald-600" />
                  <h3 className="font-bold text-sm text-slate-900">Google Sheets Audit & Re-sync</h3>
                </div>
                <p className="text-xs text-slate-500">
                  Spreadsheet ID: <code className="bg-slate-100 px-1 py-0.5 rounded text-slate-700 font-mono text-[11px]">184qGjXRADe6RLzAlBy3LGk78xzkUa8GXeqkBOzWvkWI</code>
                </p>
                <div className="space-y-2">
                  <button
                    onClick={handleResyncToSheet}
                    disabled={syncingSheet}
                    className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    <RefreshCw className={`w-4 h-4 ${syncingSheet ? "animate-spin" : ""}`} />
                    <span>Run Re-sync to Sheet (Durable Writes)</span>
                  </button>

                  <button
                    onClick={handleRunReconcile}
                    className="w-full py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Run Database vs Sheet Reconciliation Check</span>
                  </button>
                </div>

                {reconcileReport && (
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1">
                    <p className="font-bold text-slate-800">Reconciliation Results:</p>
                    <p className="text-slate-600">DB Completed Attempts: <strong>{reconcileReport.db_completed_count}</strong></p>
                    <p className="text-slate-600">Sheet Synced Count: <strong>{reconcileReport.sheet_synced_count}</strong></p>
                    <p className="text-slate-600">Pending Retry Queue: <strong>{reconcileReport.pending_writes_count}</strong></p>
                    <p className="font-semibold text-emerald-700">{reconcileReport.message}</p>
                  </div>
                )}
              </div>

              {/* Reset Candidates & Database */}
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
                <div className="flex items-center gap-2">
                  <RotateCcw className="w-5 h-5 text-rose-600" />
                  <h3 className="font-bold text-sm text-slate-900">Exam State Management</h3>
                </div>
                <p className="text-xs text-slate-500">
                  Wipe test attempts to allow candidates to start from question 1 fresh. Candidates are restricted to 1 attempt unless reset.
                </p>
                <button
                  onClick={handleResetAllAttempts}
                  className="w-full py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs flex items-center justify-center gap-2 cursor-pointer"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Wipe / Reset All Test Attempts (Clean Start)</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Candidate Review Drawer */}
      {candidateDetails && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-2xl bg-white h-full p-6 sm:p-8 flex flex-col justify-between overflow-y-auto animate-fadeIn">
            <div className="space-y-6">
              <div className="flex items-center justify-between pb-4 border-b border-slate-200">
                <div>
                  <h3 className="text-lg font-bold text-slate-900">{candidateDetails.full_name}</h3>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">
                    {candidateDetails.employee_code} • {candidateDetails.department || "HR"}
                  </p>
                </div>
                <button
                  onClick={() => setCandidateDetails(null)}
                  className="p-2 text-slate-400 hover:text-slate-600 rounded-lg cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Scorecard Hero */}
              <div className="p-5 rounded-2xl bg-brand-50 border border-brand-200 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-brand-700 uppercase">Score Secured</p>
                  <p className="text-3xl font-extrabold text-brand-900 font-mono">
                    {candidateDetails.score} <span className="text-lg text-brand-600 font-normal">/ 100</span>
                  </p>
                  <p className="text-xs text-brand-700 mt-0.5">
                    Status: <strong className={candidateDetails.score >= 35 ? "text-emerald-700" : "text-rose-700"}>
                      {candidateDetails.score >= 35 ? "PASS" : "FAIL"}
                    </strong>
                  </p>
                </div>

                <a
                  href={`/api/admin/export/pdf/${candidateDetails.attempt_id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-2 rounded-xl bg-white border border-brand-200 text-brand-700 text-xs font-semibold shadow-xs hover:bg-brand-100 flex items-center gap-1.5"
                >
                  <FileText className="w-4 h-4" />
                  <span>Download Scorecard PDF</span>
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
