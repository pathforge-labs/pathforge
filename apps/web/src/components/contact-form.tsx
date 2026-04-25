"use client";

import { useState, type FormEvent, type ReactElement } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowRight, CheckCircle2, ChevronDown, Loader2, Shield, Lock } from "lucide-react";
import { useTurnstile } from "@/hooks/use-turnstile";

type ContactState = "idle" | "loading" | "success" | "error";

interface ContactFormProps {
  className?: string;
}

export function ContactForm({ className = "" }: ContactFormProps): ReactElement {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [state, setState] = useState<ContactState>("idle");
  const [feedback, setFeedback] = useState("");
  const { containerRef: turnstileRef, execute: executeTurnstile, reset: resetTurnstile } = useTurnstile();

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();

    if (!name.trim() || !email.trim() || !subject.trim() || !message.trim()) {
      return;
    }

    setState("loading");

    try {
      // Run Turnstile challenge at submit time (execute-on-demand mode)
      const turnstileToken = await executeTurnstile();

      const response = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          subject: subject.trim(),
          message: message.trim(),
          turnstileToken: turnstileToken || undefined,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setState("success");
        setFeedback(data.message || "Message sent successfully!");
        setName("");
        setEmail("");
        setSubject("");
        setMessage("");
      } else {
        setState("error");
        setFeedback(data.error || "Something went wrong.");
      }
    } catch {
      setState("error");
      setFeedback("Network error. Please try again.");
      resetTurnstile();
    }
  }

  if (state === "success") {
    return (
      <div
        className={`flex flex-col items-center justify-center gap-4 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 px-6 py-12 text-center ${className}`}
      >
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/10">
          <CheckCircle2 className="h-7 w-7 text-emerald-400" />
        </div>
        <div>
          <p className="text-base font-semibold text-foreground">{feedback}</p>
          <p className="mt-1.5 text-sm text-muted-foreground">
            We&apos;ll get back to you within 24–48 hours.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setState("idle")}
          className="mt-2 cursor-pointer text-xs font-medium text-primary transition-colors hover:text-primary/80"
        >
          Send another message
        </button>
      </div>
    );
  }

  return (
    <div className={className}>
      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-4"
      >
        {/* Name + Email row */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label
              htmlFor="contact-name"
              className="mb-1.5 block text-xs font-medium text-muted-foreground"
            >
              Name
            </label>
            <Input
              id="contact-name"
              type="text"
              autoComplete="name"
              placeholder="Your name"
              value={name}
              onChange={(event) => {
                setName(event.target.value);
                if (state === "error") setState("idle");
              }}
              required
              maxLength={100}
              className="h-11 rounded-xl border-border/30 bg-background/40 placeholder:text-muted-foreground/40 focus:border-primary/40 focus:ring-1 focus:ring-primary/20"
            />
          </div>
          <div>
            <label
              htmlFor="contact-email"
              className="mb-1.5 block text-xs font-medium text-muted-foreground"
            >
              Email
            </label>
            <Input
              id="contact-email"
              type="email"
              autoComplete="email"
              placeholder="your@email.com"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                if (state === "error") setState("idle");
              }}
              required
              className="h-11 rounded-xl border-border/30 bg-background/40 placeholder:text-muted-foreground/40 focus:border-primary/40 focus:ring-1 focus:ring-primary/20"
            />
          </div>
        </div>

        {/* Subject */}
        <div>
          <label
            htmlFor="contact-subject"
            className="mb-1.5 block text-xs font-medium text-muted-foreground"
          >
            Subject
          </label>
          <div className="relative">
            <select
              id="contact-subject"
              autoComplete="off"
              value={subject}
              onChange={(event) => {
                setSubject(event.target.value);
                if (state === "error") setState("idle");
              }}
              required
              className="h-11 w-full cursor-pointer appearance-none rounded-xl border border-border/30 bg-background/40 px-4 pr-10 text-sm text-foreground outline-none transition-all duration-200 focus:border-primary/40 focus:ring-1 focus:ring-primary/20 [&>option]:bg-background [&>option]:text-foreground"
            >
              <option value="">Select a subject…</option>
              <option value="General Inquiry">General Inquiry</option>
              <option value="Feature Request">Feature Request</option>
              <option value="Bug Report">Bug Report</option>
              <option value="Business / Partnerships">Business / Partnerships</option>
              <option value="Press / Media">Press / Media</option>
              <option value="Other">Other</option>
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/50" />
          </div>
        </div>

        {/* Message */}
        <div>
          <label
            htmlFor="contact-message"
            className="mb-1.5 block text-xs font-medium text-muted-foreground"
          >
            Message
          </label>
          <textarea
            id="contact-message"
            autoComplete="off"
            placeholder="Tell us more about your inquiry..."
            value={message}
            onChange={(event) => {
              setMessage(event.target.value);
              if (state === "error") setState("idle");
            }}
            required
            rows={5}
            maxLength={5000}
            className="w-full resize-none rounded-xl border border-border/30 bg-background/40 px-4 py-3 text-sm text-foreground outline-none transition-all duration-200 placeholder:text-muted-foreground/40 focus:border-primary/40 focus:ring-1 focus:ring-primary/20"
          />
        </div>

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
              Send Message <ArrowRight className="ml-1.5 h-4 w-4" />
            </>
          )}
        </Button>

        {/* Cloudflare Turnstile invisible widget */}
        <div ref={turnstileRef} className="hidden" />
      </form>

      {state === "error" && (
        <p className="mt-3 text-sm text-destructive">{feedback}</p>
      )}

      <div className="mt-3 flex items-center justify-center gap-4 text-[11px] text-muted-foreground/60">
        <span className="flex items-center gap-1"><Shield className="h-3 w-3" />GDPR compliant</span>
        <span className="h-3 w-px bg-border/30" />
        <span className="flex items-center gap-1"><Lock className="h-3 w-3" />Your data is safe</span>
      </div>

    </div>
  );
}
