"use client";

import { useState, type ReactElement } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authApi } from "@/lib/api-client/auth";

export default function ResetPasswordPage(): ReactElement {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    setError("");

    if (!token) {
      setError("Invalid reset link. Please request a new one.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    const complexityErrors: string[] = [];
    if (!/[A-Z]/.test(newPassword)) complexityErrors.push("one uppercase letter");
    if (!/\d/.test(newPassword)) complexityErrors.push("one digit");
    if (!/[!@#$%^&*(),.?":{}|<>\-_=+[\]\\/\'`~;]/.test(newPassword)) complexityErrors.push("one special character");
    if (complexityErrors.length > 0) {
      setError(`Password must contain at least ${complexityErrors.join(", ")}`);
      return;
    }

    setLoading(true);

    try {
      await authApi.resetPassword({ token, new_password: newPassword });
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset password");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <Card className="border-0 shadow-none">
        <CardHeader className="space-y-1 px-0">
          <CardTitle className="text-2xl font-bold">Password reset!</CardTitle>
          <CardDescription>
            Your password has been successfully updated. You can now sign in with your new password.
          </CardDescription>
        </CardHeader>
        <CardContent className="px-0">
          <Button
            className="w-full"
            onClick={() => router.push("/login")}
          >
            Go to Login
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!token) {
    return (
      <Card className="border-0 shadow-none">
        <CardHeader className="space-y-1 px-0">
          <CardTitle className="text-2xl font-bold">Invalid reset link</CardTitle>
          <CardDescription>
            This password reset link is invalid or has expired.
          </CardDescription>
        </CardHeader>
        <CardContent className="px-0">
          <Link href="/forgot-password">
            <Button className="w-full">Request a new link</Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-0 shadow-none">
      <CardHeader className="space-y-1 px-0">
        <CardTitle className="text-2xl font-bold">Set a new password</CardTitle>
        <CardDescription>
          Enter your new password below.
        </CardDescription>
      </CardHeader>
      <CardContent className="px-0">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="newPassword">New Password</Label>
            <Input
              id="newPassword"
              type="password"
              autoComplete="new-password"
              placeholder="Min. 8 characters"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirmPassword">Confirm Password</Label>
            <Input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              placeholder="••••••••"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Resetting..." : "Reset Password"}
          </Button>
        </form>
        <p className="mt-6 text-center text-sm text-muted-foreground">
          <Link href="/login" className="font-medium text-primary underline-offset-4 hover:underline">
            Back to login
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
