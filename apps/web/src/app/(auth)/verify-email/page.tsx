"use client";

import { useState, useEffect, type ReactElement } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authApi } from "@/lib/api-client/auth";

/**
 * /verify-email
 *
 * Click-target for the link inside the verification email. Reads the
 * verification ``token`` from the URL, POSTs it to
 * ``/api/v1/auth/verify-email``, and shows the result.
 *
 * Failure-state UX (Sprint 39 audit F34):
 *   When verification fails (expired token, replayed link, network
 *   blip), the page now offers a one-click "Resend" button instead
 *   of the previous dead-end ""Go to Login"" CTA. The email address
 *   is read from the ``email`` query parameter that
 *   ``EmailService.send_verification_email`` appends to the URL —
 *   if it is absent (older links) the user types their address
 *   inline. Either way the resend goes through the normal
 *   ``/auth/resend-verification`` endpoint, which is rate-limited
 *   per-IP *and* per-account (5-minute cooldown) — enumeration
 *   protection is preserved end-to-end.
 */
export default function VerifyEmailPage(): ReactElement {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const emailFromUrl = searchParams.get("email") ?? "";

  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  // Resend-form local state (only used in the error branch)
  const [resendEmail, setResendEmail] = useState(emailFromUrl);
  const [resendStatus, setResendStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [resendError, setResendError] = useState("");

  useEffect(() => {
    if (!token) return;

    const verify = async (): Promise<void> => {
      try {
        const result = await authApi.verifyEmail({ token });
        setStatus("success");
        setMessage(result.message);
      } catch (err) {
        setStatus("error");
        setMessage(err instanceof Error ? err.message : "Verification failed");
      }
    };

    verify();
  }, [token]);

  const handleResend = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    setResendError("");

    if (!resendEmail) {
      setResendError("Please enter the email you registered with.");
      return;
    }

    setResendStatus("sending");
    try {
      // The backend always returns 200 (anti-enumeration). If the
      // account is already verified, doesn't exist, or is inside the
      // 5-min cooldown, no email is sent — but the UX is identical.
      // We keep the success copy generic to mirror that contract.
      await authApi.resendVerification({ email: resendEmail });
      setResendStatus("sent");
    } catch (err) {
      setResendStatus("error");
      setResendError(err instanceof Error ? err.message : "Could not request a new link.");
    }
  };

  if (!token) {
    return (
      <Card className="border-0 shadow-none">
        <CardHeader className="space-y-1 px-0">
          <CardTitle className="text-2xl font-bold">Invalid verification link</CardTitle>
          <CardDescription>This link is invalid or has expired. Please request a new one.</CardDescription>
        </CardHeader>
        <CardContent className="px-0">
          <Link href="/login">
            <Button className="w-full">Go to Login</Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  if (status === "loading") {
    return (
      <Card className="border-0 shadow-none">
        <CardHeader className="space-y-1 px-0">
          <CardTitle className="text-2xl font-bold">Verifying your email...</CardTitle>
          <CardDescription>Please wait while we verify your email address.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (status === "success") {
    return (
      <Card className="border-0 shadow-none">
        <CardHeader className="space-y-1 px-0">
          <CardTitle className="text-2xl font-bold">Email verified! 🎉</CardTitle>
          <CardDescription>{message}</CardDescription>
        </CardHeader>
        <CardContent className="px-0">
          <Button className="w-full" onClick={() => router.push("/login")}>
            Sign in to your account
          </Button>
        </CardContent>
      </Card>
    );
  }

  // ── Error branch — verification failed ─────────────────────
  return (
    <Card className="border-0 shadow-none">
      <CardHeader className="space-y-1 px-0">
        <CardTitle className="text-2xl font-bold">Verification failed</CardTitle>
        <CardDescription>
          {message} You can request a new verification link below.
        </CardDescription>
      </CardHeader>
      <CardContent className="px-0 space-y-4">
        {resendStatus === "sent" ? (
          <p className="rounded-lg border border-green-500/20 bg-green-500/5 px-4 py-3 text-sm text-green-500">
            If an unverified account with that email exists, a new verification link has been sent.
            Check your inbox (and spam folder).
          </p>
        ) : (
          <form onSubmit={handleResend} className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="resendEmail">Email address</Label>
              <Input
                id="resendEmail"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={resendEmail}
                onChange={(e) => setResendEmail(e.target.value)}
                required
                disabled={resendStatus === "sending"}
              />
            </div>
            {resendError && (
              <p className="text-sm text-destructive">{resendError}</p>
            )}
            <Button type="submit" className="w-full" disabled={resendStatus === "sending"}>
              {resendStatus === "sending" ? "Sending..." : "Send a new verification link"}
            </Button>
          </form>
        )}
        <Link href="/login">
          <Button variant="outline" className="w-full">
            Back to Login
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}
