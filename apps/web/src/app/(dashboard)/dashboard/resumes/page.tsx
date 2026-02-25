"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { parseResume } from "@/lib/api-client/ai";
import type { ParseResumeResponse } from "@/types/api/ai";

export default function ResumesPage() {
  const router = useRouter();
  const [rawText, setRawText] = useState("");
  const [parsed, setParsed] = useState<ParseResumeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleParse = async () => {
    if (rawText.length < 50) {
      setError("Please enter at least 50 characters of resume text.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await parseResume(rawText);
      setParsed(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to parse resume.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Resume Manager</h1>
        <p className="text-muted-foreground">
          Parse, analyze, and manage your career documents.
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-500">
          {error}
        </div>
      )}

      {/* Upload / Parse Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <span className="text-xl">📄</span>
            <div>
              <CardTitle className="text-base">Parse Resume</CardTitle>
              <CardDescription>Paste your resume text for AI-powered extraction.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            placeholder="Paste your resume/CV text here..."
            className="min-h-[200px] w-full rounded-lg border border-border bg-background px-4 py-3 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary resize-none"
          />
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              {rawText.length} characters
            </p>
            <Button onClick={handleParse} disabled={loading || rawText.length < 50}>
              {loading ? (
                <><span className="mr-2 animate-spin">⟳</span>Parsing…</>
              ) : (
                <>🔍 Parse Resume</>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Parsed Result */}
      {parsed && (
        <Card className="border-primary/20">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xl">✅</span>
                <div>
                  <CardTitle className="text-base">Parsed Resume</CardTitle>
                  <CardDescription>AI-extracted structured data</CardDescription>
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setParsed(null)}>
                ✕
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Contact Info */}
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="text-xs font-medium text-muted-foreground">Full Name</label>
                <p className="mt-0.5 text-sm font-semibold">{parsed.full_name || "—"}</p>
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Email</label>
                <p className="mt-0.5 text-sm">{parsed.email || "—"}</p>
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Location</label>
                <p className="mt-0.5 text-sm">{parsed.location || "—"}</p>
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Phone</label>
                <p className="mt-0.5 text-sm">{parsed.phone || "—"}</p>
              </div>
            </div>

            {/* Summary */}
            {parsed.summary && (
              <>
                <Separator />
                <div>
                  <label className="text-xs font-medium text-muted-foreground">Summary</label>
                  <p className="mt-1 text-sm leading-relaxed">{parsed.summary}</p>
                </div>
              </>
            )}

            {/* Skills */}
            {parsed.skills.length > 0 && (
              <>
                <Separator />
                <div>
                  <label className="text-xs font-medium text-muted-foreground">
                    Skills ({parsed.skills.length})
                  </label>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {parsed.skills.map((skill, i) => (
                      <Badge key={i} variant="secondary" className="text-xs">
                        {skill.name}
                        {skill.category && (
                          <span className="ml-1 text-muted-foreground">· {skill.category}</span>
                        )}
                      </Badge>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* Experience */}
            {parsed.experience.length > 0 && (
              <>
                <Separator />
                <div>
                  <label className="text-xs font-medium text-muted-foreground">
                    Experience ({parsed.experience.length})
                  </label>
                  <div className="mt-2 space-y-3">
                    {parsed.experience.map((exp, i) => (
                      <div key={i} className="rounded-lg border border-border/50 p-3">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium">{exp.title}</p>
                          {(exp.start_date || exp.end_date) && (
                            <span className="text-xs text-muted-foreground">
                              {exp.start_date} — {exp.end_date || "Present"}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">{exp.company}</p>
                        {exp.description && (
                          <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                            {exp.description}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* Education */}
            {parsed.education.length > 0 && (
              <>
                <Separator />
                <div>
                  <label className="text-xs font-medium text-muted-foreground">
                    Education ({parsed.education.length})
                  </label>
                  <div className="mt-2 space-y-2">
                    {parsed.education.map((edu, i) => (
                      <div key={i} className="rounded-md border border-border/50 p-3">
                        <p className="text-sm font-medium">{edu.degree}</p>
                        <p className="text-xs text-muted-foreground">
                          {edu.institution}
                          {edu.year && ` · ${edu.year}`}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* Certifications */}
            {parsed.certifications.length > 0 && (
              <>
                <Separator />
                <div>
                  <label className="text-xs font-medium text-muted-foreground">
                    Certifications ({parsed.certifications.length})
                  </label>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {parsed.certifications.map((cert, i) => (
                      <Badge key={i} variant="outline" className="text-xs">
                        🏅 {cert.name}
                        {cert.issuer && ` — ${cert.issuer}`}
                      </Badge>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* Languages */}
            {parsed.languages.length > 0 && (
              <>
                <Separator />
                <div>
                  <label className="text-xs font-medium text-muted-foreground">
                    Languages ({parsed.languages.length})
                  </label>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {parsed.languages.map((lang, i) => (
                      <Badge key={i} variant="outline" className="text-xs">
                        🌐 {lang.name}
                        {lang.proficiency && ` — ${lang.proficiency}`}
                      </Badge>
                    ))}
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* No Resume Yet */}
      {!parsed && rawText.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <span className="text-3xl">📋</span>
            </div>
            <div>
              <h3 className="text-lg font-semibold">No Resumes Yet</h3>
              <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                Paste your resume text above to get started, or complete
                the onboarding wizard for a guided experience.
              </p>
            </div>
            <Button variant="outline" onClick={() => router.push("/dashboard/onboarding")}>
              🚀 Start Onboarding
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
