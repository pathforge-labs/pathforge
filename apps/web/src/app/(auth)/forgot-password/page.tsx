"use client";

import { useState, type ReactElement } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authApi } from "@/lib/api-client/auth";

export default function ForgotPasswordPage(): ReactElement {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await authApi.forgotPassword({ email });
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <Card className="border-0 shadow-none">
        <CardHeader className="space-y-1 px-0">
          <CardTitle className="text-2xl font-bold">Check your email</CardTitle>
          <CardDescription>
            If an account exists for <span className="font-medium text-foreground">{email}</span>,
            we&apos;ve sent a password reset link. It may take a few minutes to arrive.
          </CardDescription>
        </CardHeader>
        <CardContent className="px-0">
          <p className="text-sm text-muted-foreground">
            Didn&apos;t receive an email?{" "}
            <button
              type="button"
              onClick={() => setSubmitted(false)}
              className="font-medium text-primary underline-offset-4 hover:underline"
            >
              Try again
            </button>
          </p>
          <p className="mt-4 text-sm text-muted-foreground">
            <Link href="/login" className="font-medium text-primary underline-offset-4 hover:underline">
              Back to login
            </Link>
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-0 shadow-none">
      <CardHeader className="space-y-1 px-0">
        <CardTitle className="text-2xl font-bold">Reset your password</CardTitle>
        <CardDescription>
          Enter your email address and we&apos;ll send you a link to reset your password.
        </CardDescription>
      </CardHeader>
      <CardContent className="px-0">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Sending..." : "Send Reset Link"}
          </Button>
        </form>
        <p className="mt-6 text-center text-sm text-muted-foreground">
          Remember your password?{" "}
          <Link href="/login" className="font-medium text-primary underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
