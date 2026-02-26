"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useOnboarding, type OnboardingStep } from "@/hooks/use-onboarding";
import { FileUpload } from "@/components/file-upload";
import { CareerDnaReadiness, DEFAULT_DIMENSIONS } from "@/components/career-dna-readiness";

/* ── Step Configuration ───────────────────────────────────── */

const STEP_CONFIG: Record<OnboardingStep, { title: string; description: string; icon: string }> = {
  upload: {
    title: "Upload Your Resume",
    description: "Upload a file or paste your resume text to get started.",
    icon: "📄",
  },
  parse: {
    title: "Review Parsed Data",
    description: "AI has extracted structured data from your resume.",
    icon: "🔍",
  },
  dna: {
    title: "Generate Career DNA™",
    description: "Creating your unique career intelligence profile.",
    icon: "🧬",
  },
  readiness: {
    title: "Your Career DNA™ Readiness",
    description: "See how ready your profile is for intelligent career guidance.",
    icon: "🎯",
  },
  dashboard: {
    title: "Ready to Go!",
    description: "Your career intelligence is active.",
    icon: "🚀",
  },
};

/* ── Page Component ───────────────────────────────────────── */

export default function OnboardingPage() {
  const router = useRouter();
  const onboarding = useOnboarding();
  const config = STEP_CONFIG[onboarding.step];
  const [inputMode, setInputMode] = useState<"file" | "paste">("file");

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Welcome to PathForge</h1>
        <p className="text-muted-foreground">
          Let&apos;s set up your career intelligence in a few simple steps.
        </p>
      </div>

      {/* Step Indicators */}
      <div className="flex items-center gap-2 overflow-x-auto">
        {onboarding.steps.map((step, index) => {
          const stepMeta = STEP_CONFIG[step];
          const isActive = index === onboarding.stepIndex;
          const isComplete = index < onboarding.stepIndex;
          return (
            <button
              key={step}
              onClick={() => onboarding.goToStep(step)}
              className={`flex shrink-0 items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium transition-all ${
                isActive
                  ? "bg-primary text-primary-foreground"
                  : isComplete
                    ? "bg-primary/10 text-primary cursor-pointer hover:bg-primary/20"
                    : "bg-muted text-muted-foreground cursor-not-allowed"
              }`}
              disabled={!isComplete && !isActive}
            >
              <span>{isComplete ? "✓" : stepMeta.icon}</span>
              <span className="hidden sm:inline">{stepMeta.title}</span>
              <span className="sm:hidden">{index + 1}</span>
            </button>
          );
        })}
      </div>

      {/* Error Banner */}
      {onboarding.error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-500">
          {onboarding.error}
        </div>
      )}

      {/* Step Content */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <span className="text-2xl">{config.icon}</span>
            <div>
              <CardTitle>{config.title}</CardTitle>
              <CardDescription>{config.description}</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>

          {/* ─── Step 1: Upload / Paste Resume ──────────────── */}
          {onboarding.step === "upload" && (
            <div className="space-y-4">
              {/* Mode Toggle */}
              <div className="flex gap-2">
                <Button
                  variant={inputMode === "file" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setInputMode("file")}
                >
                  📁 Upload File
                </Button>
                <Button
                  variant={inputMode === "paste" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setInputMode("paste")}
                >
                  📋 Paste Text
                </Button>
              </div>

              {/* File Upload Mode */}
              {inputMode === "file" && (
                <FileUpload
                  onFileSelect={(file) => onboarding.setFile(file)}
                  onFileRemove={() => onboarding.setFile(null)}
                  selectedFile={onboarding.file}
                  isLoading={onboarding.loading}
                />
              )}

              {/* Paste Mode */}
              {inputMode === "paste" && (
                <textarea
                  value={onboarding.rawText}
                  onChange={(event) => onboarding.setRawText(event.target.value)}
                  placeholder={"Paste your resume/CV text here...\n\nInclude your name, experience, skills, education, and any other relevant information."}
                  className="min-h-[300px] w-full rounded-lg border border-border bg-background px-4 py-3 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                />
              )}

              {/* Action */}
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground">
                  {inputMode === "paste" && (
                    <>
                      {onboarding.rawText.length} characters
                      {onboarding.rawText.length < 50 && " (minimum 50 required)"}
                    </>
                  )}
                  {inputMode === "file" && onboarding.file && (
                    <>
                      {onboarding.file.name.endsWith(".txt")
                        ? "Text file ready for parsing"
                        : "Please also paste your text below"}
                    </>
                  )}
                </p>
                <Button
                  onClick={onboarding.parseResume}
                  disabled={
                    onboarding.loading ||
                    (inputMode === "paste" && onboarding.rawText.length < 50) ||
                    (inputMode === "file" && !onboarding.file)
                  }
                >
                  {onboarding.loading ? (
                    <><span className="mr-2 animate-spin">⟳</span>Parsing…</>
                  ) : (
                    <>Parse Resume →</>
                  )}
                </Button>
              </div>
            </div>
          )}

          {/* ─── Step 2: Parse Preview ──────────────────────── */}
          {onboarding.step === "parse" && onboarding.parsedResume && (
            <div className="space-y-4">
              {/* Name & Contact */}
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="text-xs font-medium text-muted-foreground">Full Name</label>
                  <p className="mt-0.5 text-sm font-semibold">{onboarding.parsedResume.full_name || "—"}</p>
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground">Email</label>
                  <p className="mt-0.5 text-sm">{onboarding.parsedResume.email || "—"}</p>
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground">Location</label>
                  <p className="mt-0.5 text-sm">{onboarding.parsedResume.location || "—"}</p>
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground">Phone</label>
                  <p className="mt-0.5 text-sm">{onboarding.parsedResume.phone || "—"}</p>
                </div>
              </div>

              {/* Summary */}
              {onboarding.parsedResume.summary && (
                <>
                  <Separator />
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Summary</label>
                    <p className="mt-1 text-sm leading-relaxed">{onboarding.parsedResume.summary}</p>
                  </div>
                </>
              )}

              {/* Skills */}
              {onboarding.parsedResume.skills.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">
                      Skills ({onboarding.parsedResume.skills.length})
                    </label>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {onboarding.parsedResume.skills.map((skill, skillIndex) => (
                        <Badge key={skillIndex} variant="secondary" className="text-xs">
                          {skill.name}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* Experience */}
              {onboarding.parsedResume.experience.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">
                      Experience ({onboarding.parsedResume.experience.length})
                    </label>
                    <div className="mt-2 space-y-2">
                      {onboarding.parsedResume.experience.map((exp, expIndex) => (
                        <div key={expIndex} className="rounded-md border border-border/50 p-3">
                          <p className="text-sm font-medium">{exp.title}</p>
                          <p className="text-xs text-muted-foreground">{exp.company}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              <Separator />

              {/* Actions */}
              <div className="flex items-center justify-between">
                <Button variant="outline" onClick={() => onboarding.goToStep("upload")}>
                  ← Re-upload
                </Button>
                <Button onClick={onboarding.generateCareerDna} disabled={onboarding.loading}>
                  {onboarding.loading ? (
                    <><span className="mr-2 animate-spin">⟳</span>Generating…</>
                  ) : (
                    <>Generate Career DNA™ →</>
                  )}
                </Button>
              </div>
            </div>
          )}

          {/* ─── Step 3: Career DNA Generation Progress ─────── */}
          {onboarding.step === "dna" && (
            <div className="flex flex-col items-center gap-4 py-8">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                <span className="text-3xl animate-pulse">🧬</span>
              </div>
              <div className="text-center">
                <p className="font-medium">Generating Your Career DNA™</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Analyzing your skills, experience patterns, and career trajectory…
                </p>
              </div>
              <div className="flex flex-wrap justify-center gap-2 text-xs text-muted-foreground">
                {["Skill Genome", "Experience Blueprint", "Growth Vector", "Values Profile", "Market Position", "Career Resilience"].map(
                  (engine) => (
                    <Badge key={engine} variant="outline" className="text-[10px]">
                      {engine}
                    </Badge>
                  ),
                )}
              </div>
            </div>
          )}

          {/* ─── Step 4: Career DNA Readiness Score ────────── */}
          {onboarding.step === "readiness" && (
            <div className="space-y-6">
              <CareerDnaReadiness
                score={onboarding.careerDna ? 65 : 0}
                dimensions={DEFAULT_DIMENSIONS.map((dimension) => ({
                  ...dimension,
                  completeness: onboarding.careerDna ? "partial" as const : "empty" as const,
                }))}
                isLoading={!onboarding.careerDna}
              />

              <div className="flex justify-end">
                <Button onClick={() => router.push("/dashboard")}>
                  Continue to Dashboard →
                </Button>
              </div>
            </div>
          )}

          {/* ─── Step 5: Dashboard Redirect ────────────────── */}
          {onboarding.step === "dashboard" && (
            <div className="flex flex-col items-center gap-4 py-8 text-center">
              <span className="text-4xl">🎉</span>
              <p className="font-medium">Setup Complete!</p>
              <p className="text-sm text-muted-foreground">
                Your Career DNA™ profile is active. Head to your dashboard to explore your career intelligence.
              </p>
              <Button onClick={() => router.push("/dashboard")}>
                Go to Dashboard →
              </Button>
            </div>
          )}

        </CardContent>
      </Card>
    </div>
  );
}
