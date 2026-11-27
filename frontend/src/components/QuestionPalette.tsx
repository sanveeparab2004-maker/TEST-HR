import React from "react";
import { CandidateQuestion, SectionInfo } from "../types";
import { Language, formatSectionName } from "../utils/language";

interface QuestionPaletteProps {
  questions: CandidateQuestion[];
  sections: SectionInfo[];
  currentIndex: number;
  answers: Record<string, number | null>;
  flagged: Record<string, boolean>;
  onSelectQuestion: (index: number) => void;
  language?: Language;
}

export const QuestionPalette: React.FC<QuestionPaletteProps> = ({
  questions,
  sections,
  currentIndex,
  answers,
  flagged,
  onSelectQuestion,
  language = "BOTH",
}) => {
  const answeredCount = Object.values(answers).filter((v) => v !== null && v !== undefined).length;
  const flaggedCount = Object.values(flagged).filter(Boolean).length;
  const unansweredCount = questions.length - answeredCount;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 sm:p-5 space-y-5">
      <div>
        <h3 className="font-bold text-slate-900 text-sm">Question Navigation</h3>
        <div className="grid grid-cols-3 gap-2 mt-3 text-center">
          <div className="p-2 rounded-xl bg-emerald-50 border border-emerald-100">
            <p className="text-base font-bold text-emerald-700">{answeredCount}</p>
            <p className="text-[10px] text-emerald-600 font-medium uppercase tracking-wider">Answered</p>
          </div>
          <div className="p-2 rounded-xl bg-amber-50 border border-amber-100">
            <p className="text-base font-bold text-amber-700">{flaggedCount}</p>
            <p className="text-[10px] text-amber-600 font-medium uppercase tracking-wider">Flagged</p>
          </div>
          <div className="p-2 rounded-xl bg-slate-50 border border-slate-200">
            <p className="text-base font-bold text-slate-700">{unansweredCount}</p>
            <p className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">Left</p>
          </div>
        </div>
      </div>

      {/* Sections & Numbers Grid */}
      <div className="space-y-4 max-h-[55vh] overflow-y-auto pr-1">
        {sections.map((sec) => {
          const secQuestions = questions.filter((q) => q.sectionId === sec.id);
          if (secQuestions.length === 0) return null;

          return (
            <div key={sec.id} className="space-y-2">
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                {formatSectionName(sec.name, language)}
              </p>
              <div className="grid grid-cols-5 gap-1.5">
                {secQuestions.map((q) => {
                  const qIndex = questions.findIndex((item) => item.id === q.id);
                  const isCurrent = qIndex === currentIndex;
                  const isAnswered = answers[q.id] !== undefined && answers[q.id] !== null;
                  const isFlag = !!flagged[q.id];

                  let btnStyle = "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100";
                  if (isCurrent) {
                    btnStyle = "bg-brand-600 text-white border-brand-600 shadow-sm ring-2 ring-brand-500/30";
                  } else if (isFlag) {
                    btnStyle = "bg-amber-100 text-amber-900 border-amber-300 font-semibold";
                  } else if (isAnswered) {
                    btnStyle = "bg-emerald-100 text-emerald-900 border-emerald-300 font-semibold";
                  }

                  return (
                    <button
                      key={q.id}
                      onClick={() => onSelectQuestion(qIndex)}
                      className={`h-8 rounded-lg text-xs font-mono transition-all border relative flex items-center justify-center cursor-pointer ${btnStyle}`}
                      title={`Question ${q.displayNumber} (${isAnswered ? "Answered" : "Unanswered"}${isFlag ? ", Flagged" : ""})`}
                    >
                      {q.displayNumber}
                      {isFlag && !isCurrent && (
                        <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
