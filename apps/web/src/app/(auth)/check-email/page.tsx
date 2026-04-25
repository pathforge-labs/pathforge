"use client";

import { type ReactElement } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function CheckEmailPage(): ReactElement {
  const searchParams = useSearchParams();
  const email = searchParams.get("email") ?? "";

  return (
    <Card className="border-0 shadow-none">
      <CardHeader className="space-y-1 px-0">
        <CardTitle className="text-2xl font-bold">Check your email</CardTitle>
        <CardDescription>
          We&apos;ve sent a verification link to{" "}
          {email ? (
            <span className="font-medium text-foreground">{email}</span>
          ) : (
            "your email address"
          )}
          . Click the link to verify your account.
        </CardDescription>
      </CardHeader>
      <CardContent className="px-0 space-y-4">
        <p className="text-sm text-muted-foreground">
          The link will expire in 24 hours. If you don&apos;t see the email, check your spam folder.
        </p>
        <div className="flex flex-col gap-3">
          <Link href="/login">
            <Button variant="outline" className="w-full">
              Go to Login
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
