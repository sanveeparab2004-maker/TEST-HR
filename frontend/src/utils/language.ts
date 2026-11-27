export type Language = "MR" | "EN" | "BOTH";

export function getInitialLanguage(): Language {
  const saved = localStorage.getItem("assess_lang");
  if (saved === "MR" || saved === "EN" || saved === "BOTH") {
    return saved as Language;
  }
  return "MR";
}

export function setStoredLanguage(lang: Language): void {
  localStorage.setItem("assess_lang", lang);
}

export function formatQuestionStem(stem: string, lang: Language): string {
  if (lang === "BOTH" || !stem) return stem;

  // Handle scenario / situational blocks (e.g., Q25)
  if (stem.includes("Scenario:") || stem.includes("परिस्थिती:")) {
    const parts = stem.split(/(?=Scenario:)/i);
    if (parts.length >= 2) {
      if (lang === "MR") {
        return parts[0].trim();
      } else {
        return parts.slice(1).join("").trim();
      }
    }
  }

  const lines = stem.split("\n").map((l) => l.trim()).filter(Boolean);
  if (lines.length <= 1) return stem;

  const hasDevanagari = (str: string) => /[\u0900-\u097F]/.test(str);

  if (lang === "MR") {
    const mrLines = lines.filter(hasDevanagari);
    if (mrLines.length > 0) return mrLines.join("\n");
  } else if (lang === "EN") {
    const enLines = lines.filter((l) => !hasDevanagari(l));
    if (enLines.length > 0) return enLines.join("\n");
  }

  return stem;
}

export function formatOptionText(text: string, lang: Language): string {
  if (lang === "BOTH" || !text) return text;

  if (text.includes(" / ")) {
    const parts = text.split(" / ");
    if (parts.length >= 2) {
      if (lang === "MR") {
        return parts[0].trim();
      } else if (lang === "EN") {
        return parts[1].trim();
      }
    }
  }

  if (text.includes("\n")) {
    const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
    const hasDevanagari = (str: string) => /[\u0900-\u097F]/.test(str);
    if (lang === "MR") {
      const mrLines = lines.filter(hasDevanagari);
      if (mrLines.length > 0) return mrLines.join("\n");
    } else if (lang === "EN") {
      const enLines = lines.filter((l) => !hasDevanagari(l));
      if (enLines.length > 0) return enLines.join("\n");
    }
  }

  return text;
}

export function formatSectionName(name: string, lang: Language): string {
  if (lang === "BOTH" || !name) return name;
  if (name.includes(" (") && name.endsWith(")")) {
    const match = name.match(/^(.*?)\s*\((.*?)\)$/);
    if (match) {
      if (lang === "MR") return match[1].trim();
      if (lang === "EN") return match[2].trim();
    }
  }
  return name;
}
