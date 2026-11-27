import { UserSession, ExamData, CandidateStatus } from "../types";

const API_BASE = "/api";

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem("assess_token");
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export function getStoredDeviceToken(): string | null {
  return localStorage.getItem("assess_device_token");
}

export function setStoredDeviceToken(token: string): void {
  localStorage.setItem("assess_device_token", token);
}

export const api = {
  async lookup(employeeCode: string): Promise<{ requires_pin: boolean }> {
    const res = await fetch(`${API_BASE}/auth/lookup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ employee_code: employeeCode }),
    });
    if (!res.ok) throw new Error("Lookup failed");
    return res.json();
  },

  async login(
    employeeCode: string,
    fullName: string,
    pin?: string,
    department: string = "HR",
    extraProfile?: {
      current_department?: string;
      current_post?: string;
      mobile_number?: string;
      target_post?: string;
    }
  ): Promise<UserSession> {
    const deviceToken = getStoredDeviceToken();
    const deviceInfo = {
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      screenWidth: window.screen.width,
      screenHeight: window.screen.height,
      ...(extraProfile || {}),
    };

    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        employee_code: employeeCode,
        full_name: fullName,
        pin: pin || undefined,
        department: department,
        device_token: deviceToken || undefined,
        device_info: deviceInfo,
        current_department: extraProfile?.current_department,
        current_post: extraProfile?.current_post,
        mobile_number: extraProfile?.mobile_number,
        target_post: extraProfile?.target_post,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Authentication failed");
    }

    if (data.device_token) {
      setStoredDeviceToken(data.device_token);
    }
    localStorage.setItem("assess_token", data.access_token);
    localStorage.setItem("assess_role", data.role);
    localStorage.setItem("assess_emp_code", data.employee_code);
    localStorage.setItem("assess_full_name", data.full_name);

    return {
      accessToken: data.access_token,
      role: data.role,
      employeeCode: data.employee_code,
      fullName: data.full_name,
      deviceToken: data.device_token,
      attemptId: data.attempt_id,
    };
  },

  async getStatus(): Promise<CandidateStatus> {
    const res = await fetch(`${API_BASE}/candidate/status`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to fetch status");
    }
    const data = await res.json();
    return {
      employeeCode: data.employee_code,
      fullName: data.full_name,
      consentAt: data.consent_at,
      status: data.status,
      startedAt: data.started_at,
      deadlineAt: data.deadline_at,
      remainingSeconds: data.remaining_seconds,
      warningCount: data.warning_count,
      showScore: data.show_score,
      score: data.score,
      percentage: data.percentage,
      band: data.band,
    };
  },

  async giveConsent(): Promise<{ message: string; consent_at: string }> {
    const res = await fetch(`${API_BASE}/candidate/consent`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ consent: true }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to record consent");
    }
    return res.json();
  },

  async getExam(): Promise<ExamData> {
    const res = await fetch(`${API_BASE}/candidate/exam`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to load exam");
    }
    const data = await res.json();
    return {
      assessmentTitle: data.assessment_title,
      durationMinutes: data.duration_minutes,
      remainingSeconds: data.remaining_seconds,
      startedAt: data.started_at,
      deadlineAt: data.deadline_at,
      sections: data.sections.map((s: any) => ({
        id: s.id,
        name: s.name,
        sortOrder: s.sort_order,
        questionCount: s.question_count,
      })),
      questions: data.questions.map((q: any) => ({
        id: q.id,
        displayNumber: q.display_number,
        sourceNumber: q.source_number,
        stem: q.stem,
        marks: q.marks,
        sectionId: q.section_id,
        sectionName: q.section_name,
        options: q.options.map((o: any) => ({
          id: o.id,
          label: o.label,
          text: o.text,
        })),
      })),
      answers: data.answers || {},
      flagged: data.flagged || {},
      warningCount: data.warning_count,
      status: data.status,
    };
  },

  async saveAnswer(
    questionId: number,
    optionId?: number | null,
    flagged?: boolean
  ): Promise<{ status: string; remaining_seconds: number }> {
    const res = await fetch(`${API_BASE}/candidate/answer`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        question_id: questionId,
        option_id: optionId === undefined ? undefined : optionId,
        flagged: flagged === undefined ? undefined : flagged,
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to save answer");
    }
    return res.json();
  },

  async submitExam(answers?: Record<string, number | null>): Promise<any> {
    const res = await fetch(`${API_BASE}/candidate/submit`, {
      method: "POST",
      headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ answers: answers || {} }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Submission failed");
    }
    return res.json();
  },

  logout(): void {
    localStorage.removeItem("assess_token");
    localStorage.removeItem("assess_role");
    localStorage.removeItem("assess_emp_code");
    localStorage.removeItem("assess_full_name");
  },
};
