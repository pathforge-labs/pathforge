"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MatchCard } from "@/components/match-card";
import { tailorCV } from "@/lib/api-client/ai";
import { useResumes } from "@/hooks/api/use-resumes";
import { useMatches } from "@/hooks/api/use-matches";
import type { TailorCVResponse } from "@/types/api/ai";

export default function MatchesPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [tailoringId, setTailoringId] = useState<string | null>(null);
  const [tailorResult, setTailorResult] = useState<TailorCVResponse | null>(null);

  const { data: resumes, isLoading: resumesLoading, isError: resumesError } = useResumes();
  const resumeId = resumes?.[0]?.id ?? null;

  const { data: matchData, isLoading: matchesLoading, isError: matchesError } = useMatches(resumeId);
  const matches = matchData?.matches ?? [];
  const loading = resumesLoading || matchesLoading;
  const fetchError = resumesError || matchesError;

  const handleTailorCV = useCallback(async (jobId: string) => {
    if (!resumeId) return;
    setTailoringId(jobId);
    try {
      const result = await tailorCV(resumeId, jobId);
      setTailorResult(result);
    } catch {
      setError("Failed to tailor CV. Please try again.");
    } finally {
      setTailoringId(null);
    }
  }, [resumeId]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Career Radar</h1>
          <p className="text-muted-foreground">
            Semantic job matches ranked by your Career DNA™ profile.
          </p>
        </div>
        {matches.length > 0 && (
          <Badge variant="secondary" className="text-sm">
            {matches.length} matches
          </Badge>
        )}
      </div>

      {/* Fetch Error */}
      {fetchError && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-500">
          Failed to load matches. Please refresh the page.
        </div>
      )}

      {/* Tailor Error */}
      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-500">
          {error}
        </div>
      )}

      {/* Tailor Result Modal/Card */}
      {tailorResult && (
        <Card className="border-primary/30 bg-primary/5">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xl">✨</span>
                <CardTitle className="text-base">Tailored CV Result</CardTitle>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setTailorResult(null)}>
                ✕
              </Button>
            </div>
            <CardDescription>
              ATS Score: {tailorResult.ats_score}%
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {tailorResult.tailored_summary && (
              <div>
                <label className="text-xs font-medium text-muted-foreground">Tailored Summary</label>
                <p className="mt-1 text-sm">{tailorResult.tailored_summary}</p>
              </div>
            )}
            {tailorResult.tailored_skills.length > 0 && (
              <div>
                <label className="text-xs font-medium text-muted-foreground">Highlighted Skills</label>
                <div className="mt-1 flex flex-wrap gap-1">
                  {tailorResult.tailored_skills.map((skill, i) => (
                    <Badge key={i} variant="default" className="text-xs">
                      {skill}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {tailorResult.diffs.length > 0 && (
              <div>
                <label className="text-xs font-medium text-muted-foreground">Changes Made</label>
                <div className="mt-1 space-y-2">
                  {tailorResult.diffs.map((diff, i) => (
                    <div key={i} className="rounded border border-border/50 p-2 text-xs">
                      <p className="font-medium">{diff.field}</p>
                      <p className="text-red-500 line-through">{diff.original}</p>
                      <p className="text-green-500">{diff.modified}</p>
                      <p className="mt-1 text-muted-foreground italic">{diff.reason}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {tailorResult.ats_suggestions.length > 0 && (
              <div>
                <label className="text-xs font-medium text-muted-foreground">ATS Suggestions</label>
                <ul className="mt-1 space-y-1 text-xs text-muted-foreground">
                  {tailorResult.ats_suggestions.map((s, i) => (
                    <li key={i}>• {s}</li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Match List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-muted-foreground animate-pulse">Finding your best matches…</div>
        </div>
      ) : matches.length > 0 ? (
        <div className="grid gap-3">
          {matches.map((match) => (
            <MatchCard
              key={match.job_id}
              match={match}
              onTailorCV={handleTailorCV}
              tailoring={tailoringId === match.job_id}
            />
          ))}
        </div>
      ) : (
        /* Empty State */
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <span className="text-3xl">🎯</span>
            </div>
            <div>
              <h3 className="text-lg font-semibold">No Matches Yet</h3>
              <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                To see job matches, you need to complete the onboarding flow:
                upload your resume, generate your career profile, and we&apos;ll find
                the best opportunities for you.
              </p>
            </div>
            <Button onClick={() => router.push("/dashboard/onboarding")}>
              🚀 Start Onboarding
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
