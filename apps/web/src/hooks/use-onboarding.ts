"use client";

import { useState, useCallback } from "react";
import {
  parseResume as apiParseResume,
  embedResume as apiEmbedResume,
  matchResume as apiMatchResume,
} from "@/lib/api-client/ai";
import type { ParseResumeResponse, MatchCandidate } from "@/types/api/ai";

export type OnboardingStep = "upload" | "parse" | "embed" | "matches";

interface OnboardingState {
  step: OnboardingStep;
  rawText: string;
  parsedResume: ParseResumeResponse | null;
  resumeId: string | null;
  matches: MatchCandidate[];
  loading: boolean;
  error: string | null;
}

const INITIAL_STATE: OnboardingState = {
  step: "upload",
  rawText: "",
  parsedResume: null,
  resumeId: null,
  matches: [],
  loading: false,
  error: null,
};

const STEPS: OnboardingStep[] = ["upload", "parse", "embed", "matches"];

export function useOnboarding() {
  const [state, setState] = useState<OnboardingState>(INITIAL_STATE);

  const setRawText = useCallback((text: string) => {
    setState((prev) => ({ ...prev, rawText: text, error: null }));
  }, []);

  const parseResume = useCallback(async () => {
    if (!state.rawText || state.rawText.length < 50) {
      setState((prev) => ({
        ...prev,
        error: "Please paste at least 50 characters of resume text.",
      }));
      return;
    }

    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const parsed = await apiParseResume(state.rawText);
      setState((prev) => ({
        ...prev,
        parsedResume: parsed,
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
  }, [state.rawText]);

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
        step: "embed",
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
        step: "matches",
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
    parseResume,
    embedResume,
    findMatches,
    setResumeId,
    goToStep,
    reset,
  };
}
