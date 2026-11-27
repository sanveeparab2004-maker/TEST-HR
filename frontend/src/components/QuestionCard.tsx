import React, { useEffect } from "react";
import { Check, Flag } from "lucide-react";
import { CandidateQuestion } from "../types";

interface QuestionCardProps {
  question: CandidateQuestion;
  selectedOptionId: number | null;
  isFlagged: boolean;
  onSelectOption: (optionId: number) => void;
  onToggleFlag: () => void;
  totalQuestions?: number;
}

export const QuestionCard: React.FC<QuestionCardProps> = ({
  question,
  selectedOptionId,
  isFlagged,
  onSelectOption,
  onToggleFlag,
  totalQuestions,
}) => {
  // Keyboard shortcut listener: 1-4 or A-D to select, F to flag
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is in an input or textarea
      if (["INPUT", "TEXTAREA"].includes((e.target as HTMLElement)?.tagName)) return;

      const key = e.key.toUpperCase();
      if (key === "F") {
        e.preventDefault();
        onToggleFlag();
      } else if (["1", "A"].includes(key) && question.options[0]) {
        e.preventDefault();
        onSelectOption(question.options[0].id);
      } else if (["2", "B"].includes(key) && question.options[1]) {
        e.preventDefault();
        onSelectOption(question.options[1].id);
      } else if (["3", "C"].includes(key) && question.options[2]) {
        e.preventDefault();
        onSelectOption(question.options[2].id);
      } else if (["4", "D"].includes(key) && question.options[3]) {
        e.preventDefault();
        onSelectOption(question.options[3].id);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [question, onSelectOption, onToggleFlag]);

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-6 secure-exam-content">
      {/* Question Header */}
      <div className="flex items-start justify-between gap-4 pb-4 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-md bg-brand-50 text-brand-700 text-xs font-semibold tracking-wide uppercase">
              {question.sectionName}
            </span>
            <span className="text-xs text-slate-400 font-medium">
              {question.marks} Marks
            </span>
          </div>
          <h2 className="text-xs font-mono text-slate-400 mt-2">
            QUESTION {question.displayNumber} OF {totalQuestions || 100}
          </h2>
        </div>

        <button
          onClick={onToggleFlag}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            isFlagged
              ? "bg-amber-100 text-amber-800 border border-amber-300"
              : "bg-slate-100 text-slate-600 hover:bg-slate-200 border border-transparent"
          }`}
          title="Flag question for review (Key: F)"
        >
          <Flag className={`w-3.5 h-3.5 ${isFlagged ? "fill-amber-600 text-amber-600" : ""}`} />
          <span>{isFlagged ? "Flagged" : "Flag for Review"}</span>
        </button>
      </div>

      {/* Question Stem */}
      <div className="text-base sm:text-lg font-medium text-slate-900 leading-relaxed whitespace-pre-line">
        {question.stem}
      </div>

      {/* Options List */}
      <div className="space-y-3 pt-2">
        {question.options.map((opt, idx) => {
          const isSelected = selectedOptionId === opt.id;
          return (
            <button
              key={opt.id}
              onClick={() => onSelectOption(opt.id)}
              className={`w-full text-left p-4 rounded-xl border-2 transition-all flex items-start gap-3.5 cursor-pointer select-none group ${
                isSelected
                  ? "border-brand-600 bg-brand-50/50 shadow-sm ring-1 ring-brand-500/30"
                  : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/70"
              }`}
            >
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold shrink-0 transition-colors ${
                  isSelected
                    ? "bg-brand-600 text-white"
                    : "bg-slate-100 text-slate-600 group-hover:bg-slate-200"
                }`}
              >
                {opt.label}
              </div>
              <div className="flex-1 text-sm text-slate-800 pt-0.5 leading-normal whitespace-pre-line">
                {opt.text}
              </div>
              <div className="shrink-0 pt-0.5">
                <div
                  className={`w-5 h-5 rounded-full border flex items-center justify-center transition-colors ${
                    isSelected
                      ? "border-brand-600 bg-brand-600 text-white"
                      : "border-slate-300 bg-white"
                  }`}
                >
                  {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-slate-100 text-xs text-slate-400">
        <span>Keyboard shortcut: Press <kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-300 rounded font-mono text-[11px] text-slate-600">A</kbd>–<kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-300 rounded font-mono text-[11px] text-slate-600">D</kbd> or <kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-300 rounded font-mono text-[11px] text-slate-600">1</kbd>–<kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-300 rounded font-mono text-[11px] text-slate-600">4</kbd> to select</span>
        <span><kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-300 rounded font-mono text-[11px] text-slate-600">F</kbd> to flag</span>
      </div>
    </div>
  );
};
