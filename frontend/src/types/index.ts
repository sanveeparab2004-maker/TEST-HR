export interface UserSession {
  accessToken: string;
  role: "CANDIDATE" | "MONITOR" | "ADMIN";
  employeeCode: string;
  fullName: string;
  deviceToken?: string;
  attemptId?: number;
}

export interface CandidateOption {
  id: number;
  label: string; // A, B, C, D
  text: string;
}

export interface CandidateQuestion {
  id: number;
  displayNumber: number;
  sourceNumber: number;
  stem: string;
  marks: number;
  sectionId: number;
  sectionName: string;
  options: CandidateOption[];
}

export interface SectionInfo {
  id: number;
  name: string;
  sortOrder: number;
  questionCount: number;
}

export interface ExamData {
  assessmentTitle: string;
  durationMinutes: number;
  remainingSeconds: number;
  startedAt: string;
  deadlineAt: string;
  sections: SectionInfo[];
  questions: CandidateQuestion[];
  answers: Record<string, number | null>; // questionId -> optionId
  flagged: Record<string, boolean>;       // questionId -> boolean
  warningCount: number;
  status: string;
}

export interface CandidateStatus {
  employeeCode: string;
  fullName: string;
  consentAt: string | null;
  status: "IN_PROGRESS" | "SUBMITTED" | "AUTO_SUBMITTED" | "VOID";
  startedAt: string | null;
  deadlineAt: string | null;
  remainingSeconds: number;
  warningCount: number;
  showScore: boolean;
  score?: number | null;
  percentage?: number | null;
  band?: string | null;
}

export interface SystemCheckState {
  cameraAllowed: boolean;
  faceDetected: boolean;
  fullscreenAvailable: boolean;
  networkOnline: boolean;
  browserSupported: boolean;
}
