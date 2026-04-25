"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ArrowRight,
  CheckCircle2,
  Loader2,
  Shield,
  Lock,
  PartyPopper,
} from "lucide-react";
import { useTurnstile } from "@/hooks/use-turnstile";

type WaitlistState = "idle" | "loading" | "success" | "returning" | "error";

interface WaitlistFormProps {
  className?: string;
  variant?: "hero" | "compact";
}

export function WaitlistForm({
  className = "",
  variant = "hero",
}: WaitlistFormProps) {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<WaitlistState>("idle");
  const [message, setMessage] = useState("");
  const { containerRef: turnstileContainerRef, execute: executeTurnstile, reset: resetTurnstile } = useTurnstile();

  async function handleSubmit(e: FormEvent): Promise<void> {
    e.preventDefault();

    if (!email.trim()) return;

    setState("loading");

    try {
      // Run Turnstile challenge at submit time (execute-on-demand mode)
      const turnstileToken = await executeTurnstile();

      const response = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          turnstileToken: turnstileToken || undefined,
        }),
      });

      const data = (await response.json()) as {
        message?: string;
        error?: string;
        isReturning?: boolean;
      };

      if (response.ok) {
        if (data.isReturning) {
          setState("returning");
          setMessage(
            data.message || "You're already on the waitlist!"
          );
        } else {
          setState("success");
          setMessage(data.message || "You're on the list!");
        }
        setEmail("");
      } else {
        setState("error");
        setMessage(data.error || "Something went wrong.");
      }
    } catch {
      setState("error");
      setMessage("Network error. Please try again.");
    }

    // Reset Turnstile for potential retry
    resetTurnstile();
  }

  // ── Success state: new subscriber ────────────────────────────
  if (state === "success") {
    return (
      <div
        className={`flex items-center gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-6 py-4 ${className}`}
      >
        <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
        <p className="text-sm font-medium text-foreground">{message}</p>
      </div>
    );
  }

  // ── Returning subscriber state ───────────────────────────────
  if (state === "returning") {
    return (
      <div
        className={`flex items-center gap-3 rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-6 py-4 ${className}`}
      >
        <PartyPopper className="h-5 w-5 shrink-0 text-cyan-400" />
        <div>
          <p className="text-sm font-medium text-foreground">{message}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            We sent you a confirmation -- check your inbox!
          </p>
        </div>
      </div>
    );
  }

  // ── Compact variant ──────────────────────────────────────────
  if (variant === "compact") {
    return (
      <form
        onSubmit={handleSubmit}
        className={`flex items-center gap-2 ${className}`}
      >
        <Input
          id="waitlist-email-compact"
          name="email"
          type="email"
          autoComplete="email"
          placeholder="Enter your email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (state === "error") setState("idle");
          }}
          required
          className="h-11 flex-1 rounded-lg border-input bg-background/50 backdrop-blur-sm"
          aria-label="Email address for waitlist"
        />
        <Button
          type="submit"
          size="lg"
          disabled={state === "loading"}
          className="h-11 cursor-pointer bg-primary text-primary-foreground hover:bg-primary/90"
        >
          {state === "loading" ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <>
              Join <ArrowRight className="ml-1 h-4 w-4" />
            </>
          )}
        </Button>
        <div ref={turnstileContainerRef} />
      </form>
    );
  }

  // ── Hero variant (default) ───────────────────────────────────
  return (
    <div className={className}>
      <div className="relative overflow-hidden rounded-2xl border border-border/30 bg-card/60 p-5 backdrop-blur-md sm:p-6">
        {/* Subtle top gradient accent */}
        <div className="absolute inset-x-0 top-0 h-px bg-linear-to-r from-transparent via-primary/30 to-transparent" />
        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-3"
        >
          <input
            id="waitlist-email-hero"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="your@email.com"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (state === "error") setState("idle");
            }}
            required
            className="h-12 w-full rounded-xl border border-border/30 bg-background/40 px-4 text-base text-foreground outline-none transition-all duration-200 placeholder:text-muted-foreground/40 focus:border-primary/40 focus:ring-1 focus:ring-primary/20"
            aria-label="Email address for waitlist"
          />
          <Button
            type="submit"
            size="lg"
            disabled={state === "loading"}
            className="h-12 w-full cursor-pointer rounded-xl bg-linear-to-r from-violet-500 via-primary to-cyan-400 text-sm font-semibold text-white shadow-lg shadow-primary/20 transition-all duration-300 hover:shadow-xl hover:shadow-primary/30 hover:brightness-110"
          >
            {state === "loading" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                Get Early Access <ArrowRight className="ml-1.5 h-4 w-4" />
              </>
            )}
          </Button>
        </form>
        {state === "error" && (
          <p className="mt-2 text-sm text-destructive">{message}</p>
        )}
        {/* Invisible Turnstile container */}
        <div ref={turnstileContainerRef} />
      </div>
      <div className="mt-3 flex items-center justify-center gap-4 text-[11px] text-muted-foreground/60">
        <span className="flex items-center gap-1"><Shield className="h-3 w-3" />GDPR compliant</span>
        <span className="h-3 w-px bg-border/30" />
        <span className="flex items-center gap-1"><Lock className="h-3 w-3" />No spam, ever</span>
        <span className="h-3 w-px bg-border/30" />
        <span>Free for early adopters</span>
      </div>
    </div>
  );
}
