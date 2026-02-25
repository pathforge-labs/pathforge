"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScoreBadge } from "@/components/score-badge";
import type { MatchCandidate } from "@/types/api/ai";

interface MatchCardProps {
  match: MatchCandidate;
  onTailorCV?: (jobId: string) => void;
  tailoring?: boolean;
}

/**
 * Job match card with score visualization and tailor action.
 */
export function MatchCard({ match, onTailorCV, tailoring }: MatchCardProps) {
  return (
    <Card className="group relative overflow-hidden transition-all duration-200 hover:shadow-lg hover:shadow-primary/5 hover:border-primary/20">
      {/* Score accent bar */}
      <div
        className="absolute left-0 top-0 h-full w-1 transition-all duration-300"
        style={{
          background:
            match.score >= 0.7
              ? "linear-gradient(to bottom, #10b981, #059669)"
              : match.score >= 0.4
                ? "linear-gradient(to bottom, #f59e0b, #d97706)"
                : "linear-gradient(to bottom, #ef4444, #dc2626)",
        }}
      />

      <CardHeader className="flex flex-row items-start gap-4 pb-3">
        <ScoreBadge score={match.score} size="md" />
        <div className="flex-1 min-w-0">
          <CardTitle className="text-base font-semibold leading-tight truncate">
            {match.title || "Untitled Position"}
          </CardTitle>
          <p className="mt-1 text-sm text-muted-foreground truncate">
            {match.company || "Company not specified"}
          </p>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              {Math.round(match.score * 100)}% match
            </Badge>
          </div>

          {onTailorCV && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onTailorCV(match.job_id)}
              disabled={tailoring}
              className="text-xs transition-colors hover:bg-primary hover:text-primary-foreground"
            >
              {tailoring ? (
                <>
                  <span className="mr-1 animate-spin">⟳</span> Tailoring…
                </>
              ) : (
                <>✨ Tailor CV</>
              )}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
