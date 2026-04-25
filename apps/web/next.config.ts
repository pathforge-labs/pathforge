import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";
import withBundleAnalyzer from "@next/bundle-analyzer";

const analyze = withBundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

const isDev = process.env.NODE_ENV === "development";

const cspDirectives = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline' ${isDev ? "'unsafe-eval'" : ""} https://challenges.cloudflare.com https://www.googletagmanager.com https://js.stripe.com https://accounts.google.com`,
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com",
  "img-src 'self' data: blob: https:",
  `connect-src 'self'${isDev ? " http://localhost:8000" : ""} https://challenges.cloudflare.com https://www.google-analytics.com https://*.google-analytics.com https://*.analytics.google.com https://region1.google-analytics.com https://*.sentry.io https://*.ingest.sentry.io https://api.stripe.com https://accounts.google.com https://login.microsoftonline.com`,
  "frame-src https://challenges.cloudflare.com https://js.stripe.com https://hooks.stripe.com https://login.microsoftonline.com",
  "worker-src 'self' blob:",
];

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-XSS-Protection", value: "1; mode=block" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), interest-cohort=()",
  },
  {
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains; preload",
  },
  {
    key: "Content-Security-Policy",
    value: cspDirectives.join("; "),
  },
];

const nextConfig: NextConfig = {
  reactStrictMode: true,

  /** Image optimization: prefer AVIF > WebP, 1-year cache */
  images: {
    formats: ["image/avif", "image/webp"],
    deviceSizes: [640, 828, 1080, 1200, 1920],
    imageSizes: [16, 32, 48, 64, 96, 128, 256],
    minimumCacheTTL: 31_536_000, // 1 year
  },

  /** Proxy API requests to FastAPI during development */
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },

  /** Security headers on all routes */
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: securityHeaders,
      },
    ];
  },
};

/**
 * Compose order (AC2/ADR-035-10):
 *   1. withSentryConfig wraps nextConfig → enables source map upload
 *   2. analyze wraps the result → bundle analysis remains outermost
 *
 * Wrong order (analyze first) would break Sentry source maps.
 */
export default analyze(
  withSentryConfig(nextConfig, {
    // Suppress noisy Sentry build logs
    silent: true,
    // Prevent source maps from being exposed to clients (v8 API)
    sourcemaps: {
      disable: true,
    },
    // Disable automatic server instrumentation (we use instrumentation.ts)
    autoInstrumentServerFunctions: false,
  }),
);
