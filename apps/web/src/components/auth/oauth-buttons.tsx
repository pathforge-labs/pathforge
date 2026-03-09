"use client";

import { useState, type ReactElement } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { authApi } from "@/lib/api-client/auth";

interface OAuthButtonsProps {
  readonly mode: "login" | "register";
}

export default function OAuthButtons({ mode }: OAuthButtonsProps): ReactElement {
  const router = useRouter();
  const [error, setError] = useState("");

  const label = mode === "login" ? "Sign in" : "Sign up";

  const handleOAuthLogin = async (provider: "google" | "microsoft", idToken: string): Promise<void> => {
    try {
      const tokens = await authApi.oauthLogin(provider, { id_token: idToken });
      localStorage.setItem("pathforge_access_token", tokens.access_token);
      localStorage.setItem("pathforge_refresh_token", tokens.refresh_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : `${provider} sign-in failed`);
    }
  };

  const handleGoogleSignIn = async (): Promise<void> => {
    setError("");
    try {
      // Google Identity Services (GIS) credential flow
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const google = (window as unknown as Record<string, any>).google as {
        accounts: {
          id: {
            initialize: (config: Record<string, unknown>) => void;
            prompt: () => void;
          };
        };
      } | undefined;

      if (!google?.accounts?.id) {
        setError("Google Sign-In is not available. Please try again later.");
        return;
      }

      google.accounts.id.initialize({
        client_id: process.env.NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID ?? "",
        callback: async (response: { credential: string }) => {
          await handleOAuthLogin("google", response.credential);
        },
      });
      google.accounts.id.prompt();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Google sign-in failed");
    }
  };

  const handleMicrosoftSignIn = async (): Promise<void> => {
    setError("");
    try {
      // Microsoft Authentication Library (MSAL.js) flow
      // @ts-expect-error — @azure/msal-browser installed when Microsoft OAuth is configured
      const msal = (await import("@azure/msal-browser")) as { PublicClientApplication: new (config: Record<string, unknown>) => { initialize: () => Promise<void>; loginPopup: (config: Record<string, unknown>) => Promise<{ idToken: string }> } };
      const { PublicClientApplication } = msal;

      const msalInstance = new PublicClientApplication({
        auth: {
          clientId: process.env.NEXT_PUBLIC_MICROSOFT_OAUTH_CLIENT_ID ?? "",
          authority: "https://login.microsoftonline.com/common",
        },
      });

      await msalInstance.initialize();

      const result = await msalInstance.loginPopup({
        scopes: ["openid", "email", "profile"],
      });

      if (result.idToken) {
        await handleOAuthLogin("microsoft", result.idToken);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Microsoft sign-in failed");
    }
  };

  return (
    <div className="space-y-3">
      {error && <p className="text-sm text-destructive text-center">{error}</p>}

      <Button
        type="button"
        variant="outline"
        className="w-full gap-2"
        onClick={handleGoogleSignIn}
      >
        <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
            fill="#4285F4"
          />
          <path
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            fill="#34A853"
          />
          <path
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            fill="#FBBC05"
          />
          <path
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            fill="#EA4335"
          />
        </svg>
        {label} with Google
      </Button>

      <Button
        type="button"
        variant="outline"
        className="w-full gap-2"
        onClick={handleMicrosoftSignIn}
      >
        <svg className="h-4 w-4" viewBox="0 0 21 21" aria-hidden="true">
          <rect x="1" y="1" width="9" height="9" fill="#f25022" />
          <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
          <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
          <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
        </svg>
        {label} with Microsoft
      </Button>
    </div>
  );
}
