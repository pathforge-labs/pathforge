import type { Metadata, Viewport } from "next";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";
import {
  APP_NAME,
  APP_TAGLINE,
  APP_COMPANY,
  APP_URL,
} from "@/config/brand";
import { ThemeProvider } from "next-themes";
import { GoogleAnalytics } from "@/components/google-analytics";
import { Providers } from "@/providers";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const plusJakartaSans = Plus_Jakarta_Sans({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["500", "600", "700", "800"],
});

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#0a0a12" },
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
  ],
};

export const metadata: Metadata = {
  title: {
    default: `${APP_NAME} — AI-Powered Career Intelligence`,
    template: `%s | ${APP_NAME}`,
  },
  description:
    "Career Intelligence Platform with Career DNA™ technology. " +
    "Semantic job matching, CV tailoring, skill gap analysis, and career threat detection. " +
    "Built in the EU, GDPR-native.",
  keywords: [
    "career intelligence",
    "career DNA",
    "AI job matching",
    "semantic resume",
    "skill gap analysis",
    "career threat detection",
    "salary intelligence",
    "career simulation",
    "GDPR career tool",
    "EU career platform",
  ],
  authors: [{ name: APP_COMPANY, url: APP_URL }],
  creator: `${APP_NAME} by ${APP_COMPANY}`,
  metadataBase: new URL(APP_URL),
  icons: {
    icon: "/brand/logo-primary.png",
    apple: "/apple-touch-icon.png",
  },

  manifest: "/site.webmanifest",
  openGraph: {
    type: "website",
    locale: "en_US",
    url: APP_URL,
    siteName: APP_NAME,
    title: `${APP_NAME} — AI-Powered Career Intelligence`,
    description:
      `Your Career, Intelligently Forged. Career DNA™ technology for semantic job matching, ` +
      `CV tailoring, and career strategy. Built in the EU.`,
    images: [
      {
        url: "/og-image.jpg",
        width: 1200,
        height: 630,
        alt: `${APP_NAME} — ${APP_TAGLINE}`,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: `${APP_NAME} — AI-Powered Career Intelligence`,
    description:
      `Your Career, Intelligently Forged. Career DNA™ technology for semantic job matching, ` +
      `CV tailoring, and career strategy.`,
    images: ["/og-image.jpg"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  ...(process.env.NEXT_PUBLIC_GSC_VERIFICATION
    ? {
        verification: {
          google: process.env.NEXT_PUBLIC_GSC_VERIFICATION,
        },
      }
    : {}),
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-scroll-behavior="smooth" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${plusJakartaSans.variable} font-sans antialiased`}
      >
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          <Providers>
            <GoogleAnalytics />
            {children}
          </Providers>
        </ThemeProvider>
      </body>
    </html>
  );
}
