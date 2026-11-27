import React, { useState, useEffect, useRef, useCallback } from "react";
import { ChevronLeft, ChevronRight, Send, Clock, WifiOff, Check, AlertCircle, CameraOff, RefreshCw, Globe } from "lucide-react";
import { CandidateQuestion, ExamData, UserSession } from "../types";
import { QuestionCard } from "./QuestionCard";
import { QuestionPalette } from "./QuestionPalette";
import { SelfCameraTile } from "./SelfCameraTile";
import { SubmissionReviewModal } from "./SubmissionReviewModal";
import { WarningModal } from "./WarningModal";
import { ProctorEngine } from "../services/proctor";
import { api } from "../services/api";
import { Language, getInitialLanguage, setStoredLanguage } from "../utils/language";

interface ExamScreenProps {
  user: UserSession;
  examData: ExamData;
  stream: MediaStream | null;
  onSubmitted: () => void;
  language?: Language;
  onLanguageChange?: (lang: Language) => void;
}

export const ExamScreen: React.FC<ExamScreenProps> = ({
  user,
  examData,
  stream,
  onSubmitted,
  language,
  onLanguageChange,
}) => {
  const [localLang, setLocalLang] = useState<Language>(getInitialLanguage());
  const currentLanguage = language || localLang;

  const handleSelectLanguage = (l: Language) => {
    if (onLanguageChange) {
      onLanguageChange(l);
    } else {
      setLocalLang(l);
      setStoredLanguage(l);
    }
  };

  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number | null>>(examData.answers || {});
  const [flagged, setFlagged] = useState<Record<string, boolean>>(examData.flagged || {});
  const [remainingSeconds, setRemainingSeconds] = useState(examData.remainingSeconds);
  const [warningCount, setWarningCount] = useState(examData.warningCount);

  // Proctoring modal & toast states
  const [activeWarning, setActiveWarning] = useState<{
    tier: string;
    kind: string;
    message: string;
    remaining: number;
    warningNumber: number;
  } | null>(null);
  const [postFinalToast, setPostFinalToast] = useState<string | null>(null);
  const [proctorMessage, setProctorMessage] = useState<{ text: string; sender: string } | null>(null);
  const [isCameraOff, setIsCameraOff] = useState(false);

  // Autosave status
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [isOffline, setIsOffline] = useState(!navigator.onLine);

  // Submission modal state
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Queue for offline autosave retry
  const pendingSaveQueue = useRef<Array<{ qId: number; optId: number | null; flag?: boolean }>>([]);
  const proctorEngineRef = useRef<ProctorEngine | null>(null);

  // Initialize Proctoring Engine on mount
  useEffect(() => {
    if (stream) {
      const engine = new ProctorEngine({
        onWarning: (tier, message, kind, remaining, warnNum) => {
          const calculatedNum = warnNum ?? (5 - remaining);
          setActiveWarning({ tier, kind, message, remaining, warningNumber: calculatedNum });
          setWarningCount(calculatedNum);
        },
        onRestart: (message, kind) => {
          setActiveWarning({ tier: "RESTART", kind, message, remaining: 0, warningNumber: 6 });
          setWarningCount(0);
          // Preserve saved answers so candidate never loses answered work
          setRemainingSeconds(3600);
          setCurrentIndex(0);
        },
        onPostFinalNoted: (kind, message) => {
          setPostFinalToast(message);
          setWarningCount((prev) => prev + 1);
          setTimeout(() => setPostFinalToast(null), 5000);
        },
        onCameraOff: (isOff) => {
          setIsCameraOff(isOff);
        },
        onProctorMessage: (msg, sender) => {
          setProctorMessage({ text: msg, sender });
          setTimeout(() => setProctorMessage(null), 10000);
        },
      });

      engine.start(stream);
      proctorEngineRef.current = engine;
    }

    return () => {
      if (proctorEngineRef.current) {
        proctorEngineRef.current.stop();
      }
    };
  }, [stream]);

  // Server clock timer countdown (1-second tick)
  useEffect(() => {
    const timer = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          handleFinalSubmit();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // Network offline/online listeners
  useEffect(() => {
    const handleOnline = () => {
      setIsOffline(false);
      flushPendingQueue();
    };
    const handleOffline = () => setIsOffline(true);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  const flushPendingQueue = async () => {
    if (pendingSaveQueue.current.length === 0) return;
    setSaving(true);
    const queue = [...pendingSaveQueue.current];
    pendingSaveQueue.current = [];

    for (const item of queue) {
      try {
        await api.saveAnswer(item.qId, item.optId, item.flag);
      } catch {
        pendingSaveQueue.current.push(item);
      }
    }
    setSaving(false);
  };

  const handleSelectOption = useCallback(
    async (optionId: number) => {
      const currentQ = examData.questions[currentIndex];
      if (!currentQ) return;

      const isSameOption = answers[currentQ.id] === optionId;
      const newOptionId = isSameOption ? null : optionId;

      setAnswers((prev) => ({ ...prev, [currentQ.id]: newOptionId }));

      setSaving(true);
      setSaveError(false);

      try {
        await api.saveAnswer(currentQ.id, newOptionId, flagged[currentQ.id]);
      } catch {
        pendingSaveQueue.current.push({
          qId: currentQ.id,
          optId: newOptionId,
          flag: flagged[currentQ.id],
        });
        setSaveError(true);
      } finally {
        setSaving(false);
      }
    },
    [currentIndex, answers, flagged, examData.questions]
  );

  const handleToggleFlag = useCallback(async () => {
    const currentQ = examData.questions[currentIndex];
    if (!currentQ) return;

    const newFlag = !flagged[currentQ.id];
    setFlagged((prev) => ({ ...prev, [currentQ.id]: newFlag }));

    try {
      await api.saveAnswer(currentQ.id, answers[currentQ.id], newFlag);
    } catch {
      pendingSaveQueue.current.push({
        qId: currentQ.id,
        optId: answers[currentQ.id],
        flag: newFlag,
      });
    }
  }, [currentIndex, flagged, answers, examData.questions]);

  const handleFinalSubmit = async () => {
    setSubmitting(true);
    if (proctorEngineRef.current) {
      proctorEngineRef.current.stop();
    }
    try {
      await api.submitExam();
      setShowReviewModal(false);
      onSubmitted();
    } catch (err: any) {
      alert("Error submitting exam: " + (err.message || "Unknown error"));
    } finally {
      setSubmitting(false);
    }
  };

  // Keyboard navigation N/P
  useEffect(() => {
    const handleNavKey = (e: KeyboardEvent) => {
      if (activeWarning || showReviewModal) return;
      if (["INPUT", "TEXTAREA"].includes((e.target as HTMLElement)?.tagName)) return;
      if (e.key.toUpperCase() === "N" && currentIndex < examData.questions.length - 1) {
        setCurrentIndex((i) => i + 1);
      } else if (e.key.toUpperCase() === "P" && currentIndex > 0) {
        setCurrentIndex((i) => i - 1);
      }
    };
    window.addEventListener("keydown", handleNavKey);
    return () => window.removeEventListener("keydown", handleNavKey);
  }, [currentIndex, examData.questions.length, activeWarning, showReviewModal]);

  const currentQuestion = examData.questions[currentIndex];
  const answeredCount = Object.values(answers).filter((v) => v !== null && v !== undefined).length;
  const progressPercent = Math.round((answeredCount / examData.questions.length) * 100);

  // Suggested pace calculation (~72s/question)
  const idealAnsweredByNow = Math.floor((3600 - remainingSeconds) / 72);
  const paceStatus = answeredCount >= idealAnsweredByNow ? "On Track" : "Running Behind";

  // Timer formatting
  const minutes = Math.floor(remainingSeconds / 60);
  const seconds = remainingSeconds % 60;
  const isAmberTime = remainingSeconds <= 8 * 60 && remainingSeconds > 2 * 60;
  const isRedTime = remainingSeconds <= 2 * 60;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between">
      {/* Offline/Reconnecting Alert Banner */}
      {isOffline && (
        <div className="bg-amber-500 text-slate-950 font-semibold text-xs py-2 px-4 flex items-center justify-center gap-2 sticky top-0 z-50 shadow">
          <WifiOff className="w-4 h-4 animate-pulse" />
          <span>Connection Lost. Answers are queued locally and will automatically flush once reconnected.</span>
        </div>
      )}

      {/* Proctor Live Message Banner */}
      {proctorMessage && (
        <div className="bg-brand-600 text-white font-semibold text-xs py-2.5 px-6 flex items-center justify-center gap-2 sticky top-0 z-50 shadow-md animate-fadeIn">
          <AlertCircle className="w-4 h-4 text-brand-200" />
          <span>Message from {proctorMessage.sender}: {proctorMessage.text}</span>
        </div>
      )}

      {/* Post-Final Warning Non-Blocking Toast Banner */}
      {postFinalToast && (
        <div className="bg-slate-900 text-amber-300 font-medium text-xs py-2.5 px-6 flex items-center justify-center gap-2 sticky top-0 z-50 shadow-md border-b border-amber-500/30 animate-fadeIn">
          <AlertCircle className="w-4 h-4 text-amber-400" />
          <span>{postFinalToast}</span>
        </div>
      )}

      {/* Top Exam Navigation Bar */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-20 px-4 sm:px-8 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div>
            <h1 className="text-sm font-bold text-slate-900 tracking-tight leading-none">
              {examData.assessmentTitle}
            </h1>
            <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-500 font-medium">
              <span>Candidate: {user.fullName} ({user.employeeCode})</span>
              <span>•</span>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                paceStatus === "On Track" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
              }`}>
                Pace: {paceStatus}
              </span>
            </div>
          </div>

          {/* Right Controls: Language Selector + Timer + Submit */}
          <div className="flex items-center gap-2 sm:gap-4">
            {/* Language Selector (मराठी | English | Both) */}
            <div className="flex items-center p-1 bg-slate-100 rounded-xl border border-slate-200">
              <div className="flex items-center gap-1 px-1.5 text-slate-500 hidden sm:flex">
                <Globe className="w-3.5 h-3.5" />
                <span className="text-[11px] font-semibold">भाषा:</span>
              </div>
              <button
                type="button"
                onClick={() => handleSelectLanguage("MR")}
                className={`px-2.5 py-1 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                  currentLanguage === "MR"
                    ? "bg-brand-600 text-white shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
                title="फक्त मराठी (Marathi)"
              >
                मराठी
              </button>
              <button
                type="button"
                onClick={() => handleSelectLanguage("EN")}
                className={`px-2.5 py-1 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                  currentLanguage === "EN"
                    ? "bg-brand-600 text-white shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
                title="Only English"
              >
                English
              </button>
              <button
                type="button"
                onClick={() => handleSelectLanguage("BOTH")}
                className={`px-2 py-1 text-[11px] font-semibold rounded-lg transition-all cursor-pointer ${
                  currentLanguage === "BOTH"
                    ? "bg-brand-600 text-white shadow-xs"
                    : "text-slate-500 hover:text-slate-800"
                }`}
                title="दोन्ही भाषा (Both Marathi & English)"
              >
                Both
              </button>
            </div>

            {/* Countdown Clock (Backend-Authoritative) */}
            <div
              className={`flex items-center gap-2 px-3 sm:px-4 py-2 rounded-xl font-mono text-sm sm:text-base font-bold transition-colors ${
                isRedTime
                  ? "bg-rose-100 text-rose-800 animate-pulse border border-rose-300"
                  : isAmberTime
                  ? "bg-amber-100 text-amber-900 border border-amber-300"
                  : "bg-slate-100 text-slate-900 border border-slate-200"
              }`}
            >
              <Clock className="w-4 h-4 shrink-0 text-slate-500" />
              <span>
                {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
              </span>
            </div>

            <button
              onClick={() => setShowReviewModal(true)}
              className="px-3 sm:px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs shadow-sm transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <Send className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Submit Test</span>
            </button>
          </div>
        </div>

        {/* Global Progress Bar */}
        <div className="w-full bg-slate-100 h-1.5 rounded-full mt-3 overflow-hidden">
          <div
            className="bg-brand-600 h-full transition-all duration-300 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto w-full p-4 sm:p-8 flex-1 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start relative">
        {/* Left Rail: Question Palette */}
        <aside className="lg:col-span-4 xl:col-span-3 order-2 lg:order-1">
          <QuestionPalette
            questions={examData.questions}
            sections={examData.sections}
            currentIndex={currentIndex}
            answers={answers}
            flagged={flagged}
            onSelectQuestion={(idx) => setCurrentIndex(idx)}
            language={currentLanguage}
          />
        </aside>

        {/* Centre: Question Card & Controls */}
        <div className="lg:col-span-8 xl:col-span-9 order-1 lg:order-2 space-y-6 relative">
          {/* Camera Off Curtain: Full-screen block if camera is interrupted */}
          {isCameraOff && (
            <div className="fixed inset-0 z-50 bg-slate-950/95 backdrop-blur-xl flex flex-col items-center justify-center p-8 text-center text-white space-y-6 animate-fadeIn">
              <div className="w-20 h-20 rounded-3xl bg-rose-600/20 border-2 border-rose-500 flex items-center justify-center text-rose-500 shadow-xl shadow-rose-950/50">
                <CameraOff className="w-10 h-10 animate-pulse" />
              </div>
              <div className="space-y-2 max-w-md">
                <h2 className="text-2xl font-extrabold text-white tracking-tight">Camera Feed Required</h2>
                <p className="text-xs text-rose-300 font-semibold tracking-wide uppercase">
                  Proctoring Invariant: Keeping your camera open is compulsory
                </p>
                <p className="text-xs text-slate-300 leading-relaxed pt-2">
                  All assessment questions and interactions are locked until your webcam feed is restored and unobstructed. Please ensure your camera is plugged in, permitted, and unblocked. Your assessment timer continues running.
                </p>
              </div>
              <button
                onClick={async () => {
                  try {
                    const newStream = await navigator.mediaDevices.getUserMedia({
                      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
                      audio: false,
                    });
                    if (stream) {
                      const newTrack = newStream.getVideoTracks()[0];
                      const oldTrack = stream.getVideoTracks()[0];
                      if (oldTrack) {
                        stream.removeTrack(oldTrack);
                        oldTrack.stop();
                      }
                      stream.addTrack(newTrack);
                    }
                    setIsCameraOff(false);
                  } catch {
                    alert("Camera access denied or unavailable. Please check your browser address bar permissions and allow camera.");
                  }
                }}
                className="px-6 py-3 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs tracking-wide shadow-lg transition-all cursor-pointer flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Re-Enable / Restore Camera</span>
              </button>
            </div>
          )}

          {currentQuestion && (
            <QuestionCard
              question={currentQuestion}
              selectedOptionId={answers[currentQuestion.id] ?? null}
              isFlagged={!!flagged[currentQuestion.id]}
              onSelectOption={handleSelectOption}
              onToggleFlag={handleToggleFlag}
              totalQuestions={examData.questions.length}
              language={currentLanguage}
            />
          )}

          {/* Bottom Navigation Buttons */}
          <div className="bg-white rounded-2xl border border-slate-200 p-4 flex items-center justify-between shadow-sm">
            <button
              onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
              disabled={currentIndex === 0}
              className="flex items-center gap-1 px-4 py-2 rounded-xl text-slate-700 bg-slate-100 hover:bg-slate-200 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold transition-all cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Previous</span>
            </button>

            <div className="flex items-center gap-2 text-xs text-slate-400">
              {saving ? (
                <span className="text-brand-600 font-medium animate-pulse">Autosaving...</span>
              ) : saveError ? (
                <span className="text-amber-600 font-medium">Offline (Queued)</span>
              ) : (
                <span className="text-emerald-600 font-medium flex items-center gap-1">
                  <Check className="w-3.5 h-3.5" /> All saved
                </span>
              )}
            </div>

            {currentIndex < examData.questions.length - 1 ? (
              <button
                onClick={() => setCurrentIndex((prev) => prev + 1)}
                className="flex items-center gap-1 px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold shadow-sm transition-all cursor-pointer"
              >
                <span>Next</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={() => setShowReviewModal(true)}
                className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-sm transition-all cursor-pointer"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Review & Submit</span>
              </button>
            )}
          </div>
        </div>
      </main>

      {/* Floating Draggable Self Camera Tile */}
      <SelfCameraTile stream={stream} warningCount={warningCount} />

      {/* Fullscreen Warning Modal (Warnings 1..5, and RESTART) */}
      {activeWarning && (
        <WarningModal
          isOpen={true}
          tier={activeWarning.tier}
          kind={activeWarning.kind}
          message={activeWarning.message}
          remainingWarnings={activeWarning.remaining}
          warningNumber={activeWarning.warningNumber}
          isRestart={activeWarning.tier === "RESTART"}
          onAcknowledge={() => {
            const wasRestart = activeWarning.tier === "RESTART";
            setActiveWarning(null);
            if (proctorEngineRef.current) {
              proctorEngineRef.current.resetViolationCooldown();
            }
            if (wasRestart) {
              window.location.reload();
            }
          }}
        />
      )}

      {/* Submission Review Modal */}
      <SubmissionReviewModal
        isOpen={showReviewModal}
        onClose={() => setShowReviewModal(false)}
        onConfirmSubmit={handleFinalSubmit}
        totalQuestions={examData.questions.length}
        answeredCount={answeredCount}
        flaggedCount={Object.values(flagged).filter(Boolean).length}
        remainingSeconds={remainingSeconds}
        loading={submitting}
      />
    </div>
  );
};
