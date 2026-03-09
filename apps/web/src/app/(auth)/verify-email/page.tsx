"use client";

import { useState, useEffect, type ReactElement } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { authApi } from "@/lib/api-client/auth";

export default function VerifyEmailPage(): ReactElement {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

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

  return (
    <Card className="border-0 shadow-none">
      <CardHeader className="space-y-1 px-0">
        <CardTitle className="text-2xl font-bold">Verification failed</CardTitle>
        <CardDescription>{message}</CardDescription>
      </CardHeader>
      <CardContent className="px-0 space-y-3">
        <Link href="/login">
          <Button variant="outline" className="w-full">
            Go to Login
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}
