"use client";

import { useState, useCallback } from "react";
import {
  parseResume as apiParseResume,
  embedResume as apiEmbedResume,
  matchResume as apiMatchResume,
} from "@/lib/api-client/ai";
import { careerDnaApi } from "@/lib/api-client";
import type { ParseResumeResponse, MatchCandidate } from "@/types/api/ai";
import type { CareerDnaProfileResponse } from "@/types/api";

/* ── Types ────────────────────────────────────────────────── */

export type OnboardingStep = "upload" | "parse" | "dna" | "readiness" | "dashboard";

interface OnboardingState {
  step: OnboardingStep;
  rawText: string;
  file: File | null;
  parsedResume: ParseResumeResponse | null;
  resumeId: string | null;
  careerDna: CareerDnaProfileResponse | null;
  matches: MatchCandidate[];
  loading: boolean;
  error: string | null;
}

const INITIAL_STATE: OnboardingState = {
  step: "upload",
  rawText: "",
  file: null,
  parsedResume: null,
  resumeId: null,
  careerDna: null,
  matches: [],
  loading: false,
  error: null,
};

const STEPS: OnboardingStep[] = ["upload", "parse", "dna", "readiness", "dashboard"];

/* ── Hook ─────────────────────────────────────────────────── */

export function useOnboarding() {
  const [state, setState] = useState<OnboardingState>(INITIAL_STATE);

  const setRawText = useCallback((text: string) => {
    setState((prev) => ({ ...prev, rawText: text, error: null }));
  }, []);

  const setFile = useCallback((file: File | null) => {
    setState((prev) => ({ ...prev, file, error: null }));
  }, []);

  const parseResume = useCallback(async () => {
    // Support file-sourced text: if file is .txt, read it
    let textToparse = state.rawText;

    if (state.file && state.file.name.toLowerCase().endsWith(".txt") && !state.rawText) {
      try {
        textToparse = await readTextFile(state.file);
      } catch {
        setState((prev) => ({
          ...prev,
          error: "Failed to read the uploaded file. Please try pasting the text instead.",
        }));
        return;
      }
    }

    if (!textToparse || textToparse.length < 50) {
      setState((prev) => ({
        ...prev,
        error: "Please provide at least 50 characters of resume text.",
      }));
      return;
    }

    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const parsed = await apiParseResume(textToparse);
      setState((prev) => ({
        ...prev,
        parsedResume: parsed,
        rawText: textToparse,
        step: "parse",
        loading: false,
      }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : "Failed to parse resume",
      }));
    }
  }, [state.rawText, state.file]);

  const generateCareerDna = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const dnaProfile = await careerDnaApi.generate();
      setState((prev) => ({
        ...prev,
        careerDna: dnaProfile,
        step: "readiness",
        loading: false,
      }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : "Failed to generate Career DNA",
      }));
    }
  }, []);

  const embedResume = useCallback(async () => {
    if (!state.resumeId) {
      setState((prev) => ({
        ...prev,
        error: "No resume ID available. Please parse your resume first.",
      }));
      return;
    }

    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      await apiEmbedResume(state.resumeId);
      setState((prev) => ({
        ...prev,
        loading: false,
      }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : "Failed to generate embedding",
      }));
    }
  }, [state.resumeId]);

  const findMatches = useCallback(async () => {
    if (!state.resumeId) return;

    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const result = await apiMatchResume(state.resumeId, 5);
      setState((prev) => ({
        ...prev,
        matches: result.matches,
        loading: false,
      }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : "Failed to find matches",
      }));
    }
  }, [state.resumeId]);

  const setResumeId = useCallback((id: string) => {
    setState((prev) => ({ ...prev, resumeId: id }));
  }, []);

  const goToStep = useCallback((step: OnboardingStep) => {
    const currentIndex = STEPS.indexOf(state.step);
    const targetIndex = STEPS.indexOf(step);
    // Only allow going back, not forward (must complete steps)
    if (targetIndex <= currentIndex) {
      setState((prev) => ({ ...prev, step, error: null }));
    }
  }, [state.step]);

  const reset = useCallback(() => {
    setState(INITIAL_STATE);
  }, []);

  const stepIndex = STEPS.indexOf(state.step);

  return {
    ...state,
    stepIndex,
    steps: STEPS,
    setRawText,
    setFile,
    parseResume,
    generateCareerDna,
    embedResume,
    findMatches,
    setResumeId,
    goToStep,
    reset,
  };
}

/* ── Utility ──────────────────────────────────────────────── */

function readTextFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
      } else {
        reject(new Error("File content is not text"));
      }
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file);
  });
}
