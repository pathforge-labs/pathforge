import Link from "next/link";
import Script from "next/script";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <div className="flex min-h-screen">
        {/* Left panel — brand */}
        <div className="hidden w-1/2 flex-col justify-between bg-primary p-10 lg:flex">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-foreground">
              <span className="text-sm font-bold text-primary">P</span>
            </div>
            <span className="text-lg font-bold tracking-tight text-primary-foreground">
              PathForge
            </span>
          </Link>
          <div>
            <blockquote className="space-y-2">
              <p className="text-lg text-primary-foreground/80">
                &quot;PathForge didn&apos;t just find me a job — it decoded my
                career trajectory and showed me opportunities I never knew
                existed.&quot;
              </p>
              <footer className="text-sm text-primary-foreground/60">
                — Career Intelligence, Reimagined
              </footer>
            </blockquote>
          </div>
        </div>

        {/* Right panel — form */}
        <div className="flex w-full items-center justify-center p-8 lg:w-1/2">
          <div className="w-full max-w-md">{children}</div>
        </div>
      </div>

      {/* Sprint 39 H6/F3: Google Identity Services — scoped to auth pages only */}
      {process.env.NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID && (
        <Script
          src="https://accounts.google.com/gsi/client"
          strategy="lazyOnload"
        />
      )}
    </>
  );
}
