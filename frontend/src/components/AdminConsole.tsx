import React, { useState, useEffect } from "react";
import {
  Users, BarChart3, BookOpen, Settings, Download, Search,
  CheckCircle2, XCircle, AlertTriangle, FileSpreadsheet, FileText,
  Sparkles, RefreshCw, KeyRound, Trash2, ArrowUpDown, ChevronRight, X, ExternalLink
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

  // Candidate Drill-Down Drawer
  const [selectedAttemptId, setSelectedAttemptId] = useState<number | null>(null);
  const [candidateDetails, setCandidateDetails] = useState<any | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [generatingAi, setGeneratingAi] = useState(false);

  // Device lock release form
  const [releaseEmpCode, setReleaseEmpCode] = useState("");
  const [releaseReason, setReleaseReason] = useState("");
  const [releaseMessage, setReleaseMessage] = useState<string | null>(null);

  // Retention purge
  const [purgeDays, setPurgeDays] = useState(90);
  const [purgeMessage, setPurgeMessage] = useState<string | null>(null);

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
    if (statusFilter === "ALL") return matchesSearch;
    if (statusFilter === "SUBMITTED") return matchesSearch && (r.status === "SUBMITTED" || r.status === "AUTO_SUBMITTED");
    if (statusFilter === "IN_PROGRESS") return matchesSearch && r.status === "IN_PROGRESS";
    if (statusFilter === "NOT_STARTED") return matchesSearch && r.status === "NOT_STARTED";
    return matchesSearch;
  });

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      {/* Top Header */}
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

        <div className="flex items-center gap-3">
          <a
            href="/api/admin/export/excel"
            download
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-semibold transition-colors"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
            <span className="hidden sm:inline">Export Excel</span>
          </a>

          <a
            href="/api/admin/export/backup"
            download
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 text-xs font-semibold transition-colors"
          >
            <Download className="w-4 h-4 text-slate-600" />
            <span className="hidden sm:inline">Backup Dump</span>
          </a>

          <button
            onClick={onLogout}
            className="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-xs font-medium text-white transition-colors"
          >
            Sign Out
          </button>
        </div>
      </header>

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
            <span>Question Bank & Answer Key</span>
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
            <span>Operations & Controls</span>
          </button>
        </div>
      </div>

      {/* Main Tab Content */}
      <main className="flex-1 p-6 sm:p-8 max-w-7xl mx-auto w-full space-y-8">
        {activeTab === "results" && (
          <>
            {/* Top Stat Cards */}
            {stats && (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Candidates</p>
                  <p className="text-2xl font-bold text-slate-900 mt-1">{stats.total_candidates}</p>
                </div>
                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
                  <p className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">Completed / Graded</p>
                  <p className="text-2xl font-bold text-emerald-700 mt-1">{stats.submitted_count}</p>
                </div>
                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
                  <p className="text-xs font-semibold text-brand-600 uppercase tracking-wider">Currently Testing</p>
                  <p className="text-2xl font-bold text-brand-700 mt-1">{stats.in_progress_count}</p>
                </div>
                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Not Started</p>
                  <p className="text-2xl font-bold text-slate-600 mt-1">{stats.not_started_count}</p>
                </div>
              </div>
            )}

            {/* Performance Band Distribution & Section Averages */}
            {stats && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Bands */}
                <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
                  <h3 className="font-bold text-sm text-slate-900">Performance Band Breakdown</h3>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-100 text-center">
                      <p className="text-lg font-bold text-emerald-700">{stats.band_distribution["Excellent"] || 0}</p>
                      <p className="text-[10px] font-semibold text-emerald-800 uppercase mt-0.5">Excellent (85+)</p>
                    </div>
                    <div className="p-3 rounded-xl bg-blue-50 border border-blue-100 text-center">
                      <p className="text-lg font-bold text-blue-700">{stats.band_distribution["Good"] || 0}</p>
                      <p className="text-[10px] font-semibold text-blue-800 uppercase mt-0.5">Good (70-84)</p>
                    </div>
                    <div className="p-3 rounded-xl bg-amber-50 border border-amber-100 text-center">
                      <p className="text-lg font-bold text-amber-700">{stats.band_distribution["Needs Improvement"] || 0}</p>
                      <p className="text-[10px] font-semibold text-amber-800 uppercase mt-0.5">Needs Imp. (50-69)</p>
                    </div>
                    <div className="p-3 rounded-xl bg-rose-50 border border-rose-100 text-center">
                      <p className="text-lg font-bold text-rose-700">{stats.band_distribution["Requires Training"] || 0}</p>
                      <p className="text-[10px] font-semibold text-rose-800 uppercase mt-0.5">Retrain (&lt;50)</p>
                    </div>
                  </div>
                </div>

                {/* Section Heatmap Averages */}
                <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-3">
                  <h3 className="font-bold text-sm text-slate-900">Team Competency Section Heat-Map</h3>
                  <div className="space-y-2">
                    {Object.entries(stats.section_averages).map(([sec, avg]) => (
                      <div key={sec} className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="font-medium text-slate-700">{sec}</span>
                          <span className="font-mono font-bold text-slate-900">{avg}%</span>
                        </div>
                        <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              avg >= 75 ? "bg-emerald-500" : avg >= 60 ? "bg-indigo-500" : "bg-amber-500"
                            }`}
                            style={{ width: `${avg}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Results Table & Search */}
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

                <div className="flex items-center gap-2">
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
                    className="p-2 text-slate-500 hover:text-slate-800 bg-slate-50 border border-slate-200 rounded-xl"
                    title="Refresh Data"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
                    <tr>
                      <th className="py-3 px-4">Employee</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Score</th>
                      <th className="py-3 px-4">Performance Band</th>
                      <th className="py-3 px-4">Warnings</th>
                      <th className="py-3 px-4">Integrity Status</th>
                      <th className="py-3 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                    {filteredResults.map((r) => {
                      const integColors: Record<string, string> = {
                        Clean: "bg-emerald-50 text-emerald-700 border-emerald-200",
                        Minor: "bg-amber-50 text-amber-700 border-amber-200",
                        "Review Needed": "bg-rose-50 text-rose-700 border-rose-200 font-bold",
                      };

                      return (
                        <tr key={r.employee_code} className="hover:bg-slate-50/60 transition-colors">
                          <td className="py-3.5 px-4">
                            <p className="font-bold text-slate-900">{r.full_name}</p>
                            <p className="text-[11px] font-mono text-slate-400">{r.employee_code} • {r.department || "HR"}</p>
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700">
                              {r.status}
                            </span>
                          </td>
                          <td className="py-3.5 px-4">
                            {r.score !== null ? (
                              <span className="font-mono font-bold text-sm text-slate-900">
                                {r.score} <span className="text-slate-400 font-normal text-xs">({r.percentage}%)</span>
                              </span>
                            ) : (
                              <span className="text-slate-400">—</span>
                            )}
                          </td>
                          <td className="py-3.5 px-4 font-semibold text-slate-800">
                            {r.band || "—"}
                          </td>
                          <td className="py-3.5 px-4 font-mono text-xs">
                            {r.warning_count} / 3
                          </td>
                          <td className="py-3.5 px-4">
                            <span className={`px-2 py-0.5 rounded-full text-[11px] border ${integColors[r.integrity_status] || "bg-slate-100 text-slate-600"}`}>
                              {r.integrity_status}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-right space-x-2">
                            {r.attempt_id ? (
                              <>
                                <button
                                  onClick={() => handleOpenCandidate(r.attempt_id!)}
                                  className="px-2.5 py-1 rounded-lg bg-brand-50 hover:bg-brand-100 text-brand-700 text-xs font-semibold transition-colors"
                                >
                                  Details
                                </button>
                                <a
                                  href={`/api/admin/export/pdf/${r.attempt_id}`}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors inline-block"
                                >
                                  PDF
                                </a>
                              </>
                            ) : (
                              <span className="text-slate-400 text-xs italic">Unattempted</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* Question Bank Viewer */}
        {activeTab === "questions" && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-6">
            <div>
              <h2 className="text-base font-bold text-slate-900">Official Question Bank & Answer Key (Admin Restricted)</h2>
              <p className="text-xs text-slate-500 mt-1">
                Showing all 50 questions across 7 competency sections with verified answers.
              </p>
            </div>

            <div className="space-y-6">
              {questionBank.map((q) => (
                <div key={q.id} className="p-5 rounded-2xl border border-slate-200 bg-slate-50/50 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold px-2 py-0.5 rounded bg-brand-50 text-brand-700">
                      {q.section}
                    </span>
                    <span className="font-mono text-slate-400 font-bold">
                      Q{q.source_number} • {q.marks} Marks
                    </span>
                  </div>

                  <p className="text-sm font-semibold text-slate-900">{q.stem}</p>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
                    {q.options.map((opt: any) => (
                      <div
                        key={opt.id}
                        className={`p-3 rounded-xl border text-xs flex items-start gap-2.5 ${
                          opt.is_correct
                            ? "border-emerald-500 bg-emerald-50/80 text-emerald-950 font-medium"
                            : "border-slate-200 bg-white text-slate-700"
                        }`}
                      >
                        <span className={`w-5 h-5 rounded flex items-center justify-center font-bold text-[11px] shrink-0 ${
                          opt.is_correct ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-600"
                        }`}>
                          {opt.label}
                        </span>
                        <span className="pt-0.5 leading-normal">{opt.text}</span>
                        {opt.is_correct && <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 ml-auto" />}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Operations & Controls */}
        {activeTab === "controls" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Device Lock Release */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center">
                  <KeyRound className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-sm text-slate-900">Release Candidate Device Lock</h3>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">
                If a candidate experiences hardware failure or cracked screen mid-exam, release their device lock so they can log in from a replacement laptop.
              </p>

              <form onSubmit={handleReleaseDeviceLock} className="space-y-3">
                <input
                  type="text"
                  required
                  placeholder="Employee Code (e.g. I-2607040)"
                  value={releaseEmpCode}
                  onChange={(e) => setReleaseEmpCode(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-300 text-xs font-mono uppercase outline-none focus:border-brand-500"
                />
                <input
                  type="text"
                  placeholder="Reason for lock release (Audited)"
                  value={releaseReason}
                  onChange={(e) => setReleaseReason(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-300 text-xs outline-none focus:border-brand-500"
                />
                <button
                  type="submit"
                  className="w-full py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-medium text-xs transition-colors"
                >
                  Release Device Lock
                </button>
              </form>

              {releaseMessage && (
                <p className="text-xs font-semibold text-brand-700 bg-brand-50 p-2.5 rounded-xl border border-brand-200">
                  {releaseMessage}
                </p>
              )}
            </div>

            {/* Retention Auto-Purge */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-rose-50 text-rose-700 flex items-center justify-center">
                  <Trash2 className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-sm text-slate-900">Data Retention Purge (DPDP Act)</h3>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">
                Permanently deletes historical violation records and snapshot images older than the retention threshold to comply with statutory privacy mandates.
              </p>

              <div className="space-y-3">
                <div>
                  <label className="text-xs text-slate-600 block mb-1">Retention Window (Days):</label>
                  <input
                    type="number"
                    min="1"
                    max="365"
                    value={purgeDays}
                    onChange={(e) => setPurgeDays(parseInt(e.target.value) || 90)}
                    className="w-full p-2.5 rounded-xl border border-slate-300 text-xs font-mono outline-none focus:border-brand-500"
                  />
                </div>
                <button
                  onClick={handlePurgeRetention}
                  className="w-full py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-medium text-xs transition-colors"
                >
                  Execute Retention Purge
                </button>
              </div>

              {purgeMessage && (
                <p className="text-xs font-semibold text-rose-700 bg-rose-50 p-2.5 rounded-xl border border-rose-200">
                  {purgeMessage}
                </p>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Candidate Drill-Down Detailed Drawer */}
      {candidateDetails && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-2xl bg-white h-full p-6 sm:p-8 flex flex-col justify-between overflow-y-auto animate-fadeIn">
            <div className="space-y-6">
              <div className="flex items-center justify-between pb-4 border-b border-slate-200">
                <div>
                  <h3 className="text-lg font-bold text-slate-900">{candidateDetails.full_name}</h3>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">
                    {candidateDetails.employee_code} • {candidateDetails.band || "In Progress"}
                  </p>
                </div>
                <button
                  onClick={() => setCandidateDetails(null)}
                  className="p-2 text-slate-400 hover:text-slate-600 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Scorecard Hero */}
              <div className="p-5 rounded-2xl bg-brand-50 border border-brand-200 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-brand-700 uppercase">Final Mark</p>
                  <p className="text-3xl font-extrabold text-brand-900 font-mono">
                    {candidateDetails.score} <span className="text-lg text-brand-600 font-normal">/ 100</span>
                  </p>
                  <p className="text-xs text-brand-700 mt-0.5">
                    Integrity Rating: <span className="font-bold">{candidateDetails.integrity_status}</span>
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

              {/* AI Development Advice Section */}
              <div className="p-5 rounded-2xl border border-purple-200 bg-purple-50/50 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-purple-600" />
                    <h4 className="text-xs font-bold text-purple-900 uppercase tracking-wider">
                      Advisory Development Insights
                    </h4>
                  </div>
                  <button
                    onClick={handleGenerateAiSummary}
                    disabled={generatingAi}
                    className="px-3 py-1 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-[11px] font-semibold flex items-center gap-1 disabled:opacity-60 cursor-pointer"
                  >
                    {generatingAi ? "Analyzing..." : "Generate AI Summary"}
                  </button>
                </div>

                {candidateDetails.ai_summary ? (
                  <div className="space-y-2 text-xs text-purple-950">
                    <p className="italic text-purple-800">{candidateDetails.ai_summary.summary_note}</p>
                    <div className="pt-2 border-t border-purple-200/60">
                      <p className="font-semibold text-purple-900">Key Strengths:</p>
                      <ul className="list-disc pl-4 text-[11px] space-y-0.5 text-purple-800">
                        {candidateDetails.ai_summary.strengths?.map((s: string, idx: number) => (
                          <li key={idx}>{s}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="pt-2 border-t border-purple-200/60">
                      <p className="font-semibold text-purple-900">Recommended Next Steps:</p>
                      <ul className="list-disc pl-4 text-[11px] space-y-0.5 text-purple-800">
                        {candidateDetails.ai_summary.recommended_training?.map((t: string, idx: number) => (
                          <li key={idx}>{t}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-purple-700">
                    Click "Generate AI Summary" to obtain structured competency analysis and personalized training recommendations (Claude model).
                  </p>
                )}
              </div>

              {/* Question-by-Question Review */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Item Analysis Review (50 Questions)
                </h4>
                <div className="space-y-2 max-h-96 overflow-y-auto pr-1 text-xs">
                  {candidateDetails.questions_review?.map((q: any) => (
                    <div
                      key={q.question_id}
                      className={`p-3 rounded-xl border flex items-start gap-3 ${
                        q.is_correct ? "border-emerald-200 bg-emerald-50/40" : "border-rose-200 bg-rose-50/40"
                      }`}
                    >
                      <span className={`w-5 h-5 rounded flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5 ${
                        q.is_correct ? "bg-emerald-600 text-white" : "bg-rose-600 text-white"
                      }`}>
                        {q.source_number}
                      </span>
                      <div className="flex-1 space-y-1">
                        <p className="font-medium text-slate-900">{q.stem}</p>
                        <p className="text-[11px] text-slate-600">
                          Candidate Selected: <span className="font-semibold">{q.selected_label || "Unanswered"}</span> — {q.selected_text}
                        </p>
                        {!q.is_correct && (
                          <p className="text-[11px] text-emerald-700 font-semibold">
                            Correct Answer: {q.correct_label} — {q.correct_text}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
