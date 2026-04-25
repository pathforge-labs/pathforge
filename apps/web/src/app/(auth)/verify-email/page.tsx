"use client";

import { useEffect, useRef, useState, type ReactElement } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
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
 *   of the previous dead-end "Go to Login" CTA. The email address
 *   is read from the ``email`` query parameter that
 *   ``EmailService.send_verification_email`` appends to the URL —
 *   if it is absent (older links) the user types their address
 *   inline. Either way the resend goes through the normal
 *   ``/auth/resend-verification`` endpoint, which is rate-limited
 *   per-IP *and* per-account (5-minute cooldown) — enumeration
 *   protection is preserved end-to-end.
 *
 * Both verify and resend are modelled as TanStack Query mutations
 * (``useMutation``) per the repo style guide. Local ``useState`` is
 * limited to controlled inputs; loading / error / success state is
 * derived from the mutation lifecycle.
 */
export default function VerifyEmailPage(): ReactElement {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const emailFromUrl = searchParams.get("email") ?? "";

  const verifyMutation = useMutation({
    mutationFn: (verifyToken: string) => authApi.verifyEmail({ token: verifyToken }),
  });

  const resendMutation = useMutation({
    mutationFn: (email: string) => authApi.resendVerification({ email }),
  });

  // Sprint 39 audit A-M6: guard against React Strict Mode
  // double-invoke and against query-param-driven re-runs. A
  // verification call must fire exactly once per page mount per
  // token value — otherwise the second call hits a 400 because the
  // first already consumed the token, and the user sees a confusing
  // "verification failed" screen for a token that just succeeded.
  const lastFiredTokenRef = useRef<string | null>(null);

  useEffect(() => {
    if (token && lastFiredTokenRef.current !== token) {
      lastFiredTokenRef.current = token;
      verifyMutation.mutate(token);
    }
    // verifyMutation is stable across renders (TanStack returns the
    // same object reference); excluding it from deps is intentional
    // to keep this single-shot.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // Resend form input — controlled by useState because the value
  // doesn't belong to a server-state mutation.
  const [resendEmail, setResendEmail] = useState(emailFromUrl);
  const [resendValidationError, setResendValidationError] = useState("");

  const handleResend = (e: React.FormEvent): void => {
    e.preventDefault();
    setResendValidationError("");

    if (!resendEmail) {
      setResendValidationError("Please enter the email you registered with.");
      return;
    }
    resendMutation.mutate(resendEmail);
  };

  // ── No token in URL — invalid landing ───────────────────────
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

  // ── Loading ─────────────────────────────────────────────────
  if (verifyMutation.isPending || verifyMutation.isIdle) {
    return (
      <Card className="border-0 shadow-none">
        <CardHeader className="space-y-1 px-0">
          <CardTitle className="text-2xl font-bold">Verifying your email...</CardTitle>
          <CardDescription>Please wait while we verify your email address.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  // ── Success ─────────────────────────────────────────────────
  if (verifyMutation.isSuccess) {
    return (
      <Card className="border-0 shadow-none">
        <CardHeader className="space-y-1 px-0">
          <CardTitle className="text-2xl font-bold">Email verified</CardTitle>
          <CardDescription>{verifyMutation.data.message}</CardDescription>
        </CardHeader>
        <CardContent className="px-0">
          <Button className="w-full" onClick={() => router.push("/login")}>
            Sign in to your account
          </Button>
        </CardContent>
      </Card>
    );
  }

  // ── Error — verify failed, offer resend ─────────────────────
  const verifyMessage =
    verifyMutation.error instanceof Error
      ? verifyMutation.error.message
      : "Verification failed";

  const resendNetworkError =
    resendMutation.isError && resendMutation.error instanceof Error
      ? resendMutation.error.message
      : "";

  return (
    <Card className="border-0 shadow-none">
      <CardHeader className="space-y-1 px-0">
        <CardTitle className="text-2xl font-bold">Verification failed</CardTitle>
        <CardDescription>
          {verifyMessage} You can request a new verification link below.
        </CardDescription>
      </CardHeader>
      <CardContent className="px-0 space-y-4">
        {resendMutation.isSuccess ? (
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
                disabled={resendMutation.isPending}
              />
            </div>
            {(resendValidationError || resendNetworkError) && (
              <p className="text-sm text-destructive">
                {resendValidationError || resendNetworkError}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={resendMutation.isPending}>
              {resendMutation.isPending ? "Sending..." : "Send a new verification link"}
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
