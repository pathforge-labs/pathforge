/**
 * PathForge — OAuthButtons Component Tests
 * ===========================================
 * Sprint Pre-40 H7: Button rendering, env-var gating, and label modes.
 *
 * Audit F9 Resolution: Module-level constants capture process.env at import
 * time. We use vi.resetModules() + dynamic import() per test so each test
 * re-evaluates the env var constants.
 *
 * Audit F11 Resolution: useRouter from next/navigation is mocked globally.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";

// F11: Mock Next.js navigation — must be before any component import
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), back: vi.fn() }),
}));

// F9: Dynamic import helper — resets module cache so env vars re-evaluate
async function importOAuthButtons(): Promise<
  (props: { mode: "login" | "register" }) => ReactElement
> {
  vi.resetModules();
  // Re-mock next/navigation after resetModules
  vi.doMock("next/navigation", () => ({
    useRouter: () => ({ push: mockPush, replace: vi.fn(), back: vi.fn() }),
  }));
  const mod = await import("@/components/auth/oauth-buttons");
  return mod.default;
}

describe("OAuthButtons", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.unstubAllEnvs();
  });

  it("should render Google button when GOOGLE_OAUTH_CLIENT_ID is set", async () => {
    vi.stubEnv("NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID", "test-google-id");
    const OAuthButtons = await importOAuthButtons();

    render(<OAuthButtons mode="login" />);

    expect(screen.getByText(/sign in with google/i)).toBeDefined();
  });

  it("should render Microsoft button when MICROSOFT_OAUTH_CLIENT_ID is set", async () => {
    vi.stubEnv("NEXT_PUBLIC_MICROSOFT_OAUTH_CLIENT_ID", "test-ms-id");
    const OAuthButtons = await importOAuthButtons();

    render(<OAuthButtons mode="login" />);

    expect(screen.getByText(/sign in with microsoft/i)).toBeDefined();
  });

  it("should render empty fragment when no providers configured", async () => {
    // No env stubs — both undefined → F18 empty fragment
    const OAuthButtons = await importOAuthButtons();

    const { container } = render(<OAuthButtons mode="register" />);

    expect(container.innerHTML).toBe("");
  });

  it("should use 'Sign up' label in register mode", async () => {
    vi.stubEnv("NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID", "test-id");
    const OAuthButtons = await importOAuthButtons();

    render(<OAuthButtons mode="register" />);

    expect(screen.getByText(/sign up with google/i)).toBeDefined();
  });

  it("should render both buttons when both providers configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID", "test-google-id");
    vi.stubEnv("NEXT_PUBLIC_MICROSOFT_OAUTH_CLIENT_ID", "test-ms-id");
    const OAuthButtons = await importOAuthButtons();

    render(<OAuthButtons mode="login" />);

    expect(screen.getByText(/sign in with google/i)).toBeDefined();
    expect(screen.getByText(/sign in with microsoft/i)).toBeDefined();
  });
});
