/**
 * PathForge — Security Settings Page (T1-extension / ADR-0011)
 * ===============================================================
 *
 * Lists every active session (refresh-token JTI) for the current
 * user with device/IP/last-seen metadata, and lets them:
 *
 *   - Revoke any one session — including the current device.
 *   - "Sign out of all other devices" — keeps the current session.
 *
 * The current session is highlighted with a `Current device` badge
 * so accidental self-logout requires an explicit click on that row.
 *
 * Hydration safety
 * ----------------
 *
 * The page intentionally uses absolute UTC timestamps for
 * `last_seen_at` until after hydration, then upgrades to relative
 * "5m ago" via the `useClientNow` hook (same pattern the AI usage
 * page uses — Gemini medium #4 on PR #35). Without this the SSR
 * markup and the first client render would disagree near the
 * minute boundary and React would warn.
 */

"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useRevokeOtherSessions,
  useRevokeSession,
  useSessions,
} from "@/hooks/api/use-sessions";
import type { SessionItem } from "@/lib/api-client/sessions";

/* ── Helpers ──────────────────────────────────────────────── */

function formatLastSeen(iso: string, now: number | null): string {
  if (!iso) return "—";
  if (now === null) {
    // Pre-hydration: show absolute UTC so SSR matches first client paint.
    return new Intl.DateTimeFormat("en-GB", {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "UTC",
    }).format(new Date(iso));
  }
  const then = new Date(iso).getTime();
  const diffMs = now - then;
  if (diffMs < 60_000) return "Just now";
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function useClientNow(): number | null {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    const initial = setTimeout(() => setNow(Date.now()), 0);
    const interval = setInterval(() => setNow(Date.now()), 60_000);
    return () => {
      clearTimeout(initial);
      clearInterval(interval);
    };
  }, []);
  return now;
}

/* ── Sub-components ───────────────────────────────────────── */

function SessionRow({
  session,
  onRevoke,
  isRevoking,
  now,
}: {
  session: SessionItem;
  onRevoke: () => void;
  isRevoking: boolean;
  now: number | null;
}) {
  return (
    <li
      className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3 py-4"
      data-testid="security-session-row"
      data-jti={session.jti}
      data-current={session.is_current ? "true" : "false"}
    >
      <div>
        <div className="flex items-center gap-2">
          <span className="font-medium">{session.device_label}</span>
          {session.is_current && (
            <Badge variant="default" data-testid="current-device-badge">
              Current device
            </Badge>
          )}
        </div>
        <div className="text-sm text-muted-foreground mt-1">
          {session.ip ? `${session.ip} · ` : ""}
          last active {formatLastSeen(session.last_seen_at, now)}
        </div>
        <div
          className="text-xs text-muted-foreground mt-1 truncate max-w-md"
          title={session.user_agent}
        >
          {session.user_agent || "Unknown user agent"}
        </div>
      </div>
      <div className="flex items-center">
        <Button
          variant="ghost"
          size="sm"
          onClick={onRevoke}
          disabled={isRevoking}
          aria-label={`Revoke session on ${session.device_label}`}
          data-testid="revoke-session-button"
        >
          {isRevoking ? "Revoking…" : "Revoke"}
        </Button>
      </div>
    </li>
  );
}

/* ── Page Component ───────────────────────────────────────── */

export default function SecuritySettingsPage() {
  const sessions = useSessions();
  const revoke = useRevokeSession();
  const revokeOthers = useRevokeOtherSessions();
  const now = useClientNow();
  const [revokingJti, setRevokingJti] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const handleRevoke = (jti: string) => {
    setRevokingJti(jti);
    setFeedback(null);
    revoke.mutate(jti, {
      onSuccess: () => setFeedback("Session revoked."),
      onError: () => setFeedback("Could not revoke session — try again."),
      onSettled: () => setRevokingJti(null),
    });
  };

  const handleRevokeOthers = () => {
    setFeedback(null);
    revokeOthers.mutate(undefined, {
      onSuccess: (data) =>
        setFeedback(
          data.revoked_count === 0
            ? "No other sessions to sign out."
            : `Signed out of ${data.revoked_count} other device${data.revoked_count === 1 ? "" : "s"}.`,
        ),
      onError: () => setFeedback("Could not sign out other devices."),
    });
  };

  const items = sessions.data?.sessions ?? [];
  const otherCount = items.filter((s) => !s.is_current).length;

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold">Security</h1>
        <p className="text-muted-foreground mt-1">
          Every device currently signed in to your account. Revoke any one,
          or sign out of all other devices in one click.
        </p>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Active sessions</CardTitle>
            <CardDescription>
              {sessions.data
                ? `${items.length} active session${items.length === 1 ? "" : "s"}`
                : "Loading…"}
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            disabled={otherCount === 0 || revokeOthers.isPending}
            onClick={handleRevokeOthers}
            aria-label="Sign out of all other devices"
            data-testid="revoke-others-button"
          >
            {revokeOthers.isPending
              ? "Signing out…"
              : `Sign out of ${otherCount} other device${otherCount === 1 ? "" : "s"}`}
          </Button>
        </CardHeader>
        <CardContent>
          {sessions.isPending && (
            <div className="space-y-3" aria-busy="true">
              <Skeleton className="h-16" />
              <Skeleton className="h-16" />
            </div>
          )}

          {sessions.isError && (
            <div role="alert" className="text-destructive">
              Could not load sessions. Try refreshing the page; if it
              still fails, our team has been notified.
            </div>
          )}

          {sessions.data && items.length === 0 && (
            <div
              className="py-12 text-center text-muted-foreground"
              data-testid="security-sessions-empty"
            >
              <p>No active sessions.</p>
              <p className="text-sm mt-2">
                If this looks wrong, sign out and back in to refresh
                the registry.
              </p>
            </div>
          )}

          {sessions.data && items.length > 0 && (
            <ul className="divide-y" data-testid="security-sessions-list">
              {items.map((session) => (
                <SessionRow
                  key={session.jti}
                  session={session}
                  isRevoking={revokingJti === session.jti}
                  now={now}
                  onRevoke={() => handleRevoke(session.jti)}
                />
              ))}
            </ul>
          )}

          {feedback && (
            <>
              <Separator className="my-4" />
              <div
                className="text-sm text-muted-foreground"
                role="status"
                data-testid="security-feedback"
              >
                {feedback}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Why we show this</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            PathForge stores your auth tokens in <code>httpOnly</code> cookies
            so JavaScript can never read them. This page lets you see exactly
            where your account is signed in, and end any session you don&apos;t
            recognise.
          </p>
          <p>
            Revoking a session signs that device out on its next API call —
            usually within a minute. Revoking your current device will sign
            you out of this browser too.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
