import dynamic from "next/dynamic";
import { WaitlistForm } from "@/components/waitlist-form";
import { AnimatedSection, HeroDashboard } from "@/components/animated-sections";
import { TestimonialAvatar } from "@/components/testimonial-avatar";
import { SpotlightCard } from "@/components/spotlight-card";
import { BorderGlow } from "@/components/border-glow";
import { CountUp } from "@/components/count-up";
import { AnimatedBar } from "@/components/animated-bar";

/* ── Below-fold code splitting ─────────────────────── */
/* eslint-disable @typescript-eslint/no-explicit-any */
const TestimonialsMarquee = dynamic(
  () =>
    import("@/components/testimonials-marquee").then((m) => m.TestimonialsMarquee) as any,
  { ssr: true }
) as React.ComponentType<{ speed?: string; children?: React.ReactNode }>;
const FaqAccordion = dynamic(
  () =>
    import("@/components/faq-accordion").then((m) => m.FaqAccordion) as any,
  { ssr: true }
) as React.ComponentType<{ items: Array<{ q: string; a: string }> }>;
const PricingCards = dynamic(
  () =>
    import("@/components/pricing-cards").then((m) => m.PricingCards) as any,
  { ssr: true }
) as React.ComponentType<Record<string, never>>;
import { OrganizationJsonLd, WebSiteJsonLd, FAQPageJsonLd } from "@/components/json-ld";
import { APP_NAME } from "@/config/brand";
import {
  FEATURES,
  STATS,
  TRUST_BADGES,
  DNA_CAPABILITIES,
  HOW_IT_WORKS,
  COMPARISON,
  TESTIMONIALS,
  FAQ,
} from "@/data/landing-data";
import {
  Dna,
  Target,
  FileText,
  DollarSign,
  Sparkles,
  ChevronRight,
  ArrowRight,
  Check,
  X,
  MessageSquareQuote,
  Linkedin,
} from "lucide-react";

/* ─────────────────────── Page (Server Component) ──── */

export default function LandingPage() {
  return (
    <>
      {/* ── Structured Data (JSON-LD) ─────────────────── */}
      <OrganizationJsonLd />
      <WebSiteJsonLd />
      <FAQPageJsonLd items={FAQ} />
        {/* ── Hero Section ────────────────────────────── */}
        <section className="noise-overlay relative overflow-hidden px-6 pb-8 pt-24 sm:pb-12 sm:pt-32 lg:pt-36">
          {/* Ambient glow effects */}
          <div
            className="pointer-events-none absolute -left-64 -top-64 h-[600px] w-[600px] rounded-full"
            style={{
              background:
                "radial-gradient(circle, oklch(0.7 0.2 270 / 10%) 0%, transparent 70%)",
            }}
          />
          <div
            className="pointer-events-none absolute -right-48 top-1/3 h-[500px] w-[500px] rounded-full"
            style={{
              background:
                "radial-gradient(circle, oklch(0.75 0.15 195 / 8%) 0%, transparent 70%)",
            }}
          />

          <div className="relative mx-auto max-w-4xl 2xl:max-w-[1000px] 3xl:max-w-[1200px] text-center">
            {/* Badge */}
            <div className="animate-fade-in mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm text-primary">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Powered by Career DNA™ Technology</span>
            </div>

            {/* Headline — display font */}
            <h1 className="animate-fade-in-up font-display mb-6 text-4xl font-extrabold tracking-tight sm:text-5xl md:text-6xl lg:text-7xl">
              Your Career,{" "}
              <span className="gradient-text-animated">
                Intelligently Forged
              </span>
            </h1>

            {/* Sub-headline */}
            <p className="animate-fade-in-up delay-200 mx-auto mb-10 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg lg:text-xl">
              {APP_NAME} uses AI to decode your unique Career DNA™ — matching you
              with opportunities that align with your skills, trajectory, and
              ambitions.{" "}
              <span className="font-medium text-foreground/80">
                Not just another job board.
              </span>
            </p>

            {/* Waitlist Form */}
            <div
              id="waitlist"
              className="animate-fade-in-up delay-400 mx-auto max-w-lg"
            >
              <WaitlistForm variant="hero" />
            </div>
          </div>

          {/* Hero Dashboard Visualization */}
          <div className="animate-fade-in-up delay-500">
            <HeroDashboard />
          </div>
        </section>

        {/* ── Stats Bar ────────────────────────────────── */}
        <section className="border-y border-border/20 bg-card/20" aria-label="Key metrics">
          <div className="mx-auto grid max-w-5xl 2xl:max-w-[1100px] 3xl:max-w-[1280px] grid-cols-2 gap-4 px-6 py-8 sm:grid-cols-4 sm:gap-0 sm:py-10">
            {STATS.map((stat, i) => (
              <AnimatedSection key={stat.label} delay={i * 80}>
                <div className={`stat-item text-center ${i < STATS.length - 1 ? "sm:border-r sm:border-border/15" : ""}`}>
                  <div className="flex items-center justify-center gap-2">
                    <stat.icon className="stat-icon h-4 w-4 text-primary/70" />
                    <span className="stat-value font-display text-2xl font-bold sm:text-3xl">
                      {/^\d+/.test(stat.value) ? (
                        <CountUp
                          end={stat.value.replace(/[^0-9]/g, "")}
                          suffix={stat.value.replace(/[0-9]/g, "")}
                        />
                      ) : (
                        stat.value
                      )}
                    </span>
                  </div>
                  <p className="mt-1 text-xs font-medium text-muted-foreground sm:text-sm">
                    {stat.label}
                  </p>
                </div>
              </AnimatedSection>
            ))}
          </div>
        </section>

        {/* ── Trust Bar ──────────────────────────────── */}
        <section className="px-6 py-8" aria-label="Trust signals">
          <div className="mx-auto flex max-w-4xl 2xl:max-w-[1000px] 3xl:max-w-[1200px] flex-col items-center justify-center gap-6 sm:flex-row sm:gap-12">
            {TRUST_BADGES.map((badge) => (
              <AnimatedSection key={badge.label}>
                <div className="group flex cursor-default items-center gap-3 rounded-xl px-3 py-2 text-sm transition-all duration-300 hover:scale-[1.03] hover:bg-primary/5">
                  <div className="trust-icon flex h-9 w-9 items-center justify-center rounded-lg bg-primary/5 transition-colors group-hover:bg-primary/10">
                    <badge.icon className="h-4 w-4 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium">{badge.label}</p>
                    <p className="text-xs text-muted-foreground">
                      {badge.sublabel}
                    </p>
                  </div>
                </div>
              </AnimatedSection>
            ))}
          </div>
        </section>

        {/* ── Section Divider ─────────────────────────── */}
        <div className="section-divider mx-auto max-w-4xl 2xl:max-w-[1000px] 3xl:max-w-[1200px]" />

        {/* ── Problem Section ────────────────────────── */}
        <section className="px-6 py-20 sm:py-28" aria-label="The problem we solve">
          <div className="mx-auto max-w-6xl 2xl:max-w-[1200px] 3xl:max-w-[1400px]">
            <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
              {/* Left — copy */}
              <AnimatedSection>
                <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-primary">
                  The Problem
                </p>
                <h2 className="font-display mb-6 text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
                  The world doesn&apos;t need another{" "}
                  <span className="text-muted-foreground line-through decoration-primary/40 decoration-2">
                    resume builder
                  </span>
                </h2>
                <p className="mb-8 max-w-lg text-base leading-relaxed text-muted-foreground lg:text-lg">
                  Existing career tools focus on formatting and keywords. They
                  optimize your resume but never ask the harder question:{" "}
                  <span className="font-medium text-foreground">
                    &ldquo;Is this even the right career move for you?&rdquo;
                  </span>
                </p>
              </AnimatedSection>

              {/* Right — problem cards */}
              <div className="grid gap-4">
                {[
                  {
                    label: "Resume Builders",
                    problem: "Format your CV, ignore your trajectory",
                    icon: FileText,
                  },
                  {
                    label: "Job Boards",
                    problem: "Keyword match, miss semantic fit",
                    icon: Target,
                  },
                  {
                    label: "Career Coaches",
                    problem: "$200/hr, limited data access",
                    icon: DollarSign,
                  },
                ].map((item, i) => (
                  <AnimatedSection key={item.label} delay={i * 120}>
                    <div className="problem-card group flex cursor-default items-center gap-4 rounded-xl p-4">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-destructive/10 transition-colors duration-300 group-hover:bg-primary/10">
                        <item.icon className="h-4 w-4 text-destructive/70 transition-colors duration-300 group-hover:text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold">{item.label}</p>
                        <p className="text-sm text-muted-foreground">
                          {item.problem}
                        </p>
                      </div>
                    </div>
                  </AnimatedSection>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── Section Divider ─────────────────────────── */}
        <div className="section-divider mx-auto max-w-4xl 2xl:max-w-[1000px] 3xl:max-w-[1200px]" />

        {/* ── The Process Section ────────────────────── */}
        <section id="process" className="px-6 py-20 sm:py-28" aria-label="How PathForge works">
          <AnimatedSection className="mx-auto max-w-3xl text-center">
            <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-primary">
              Simple Process
            </p>
            <h2 className="font-display mb-4 text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
              Three Steps to{" "}
              <span className="gradient-text">Career Clarity</span>
            </h2>
            <p className="mx-auto max-w-xl text-muted-foreground lg:text-lg">
              From upload to intelligent matches in minutes, not months.
            </p>
          </AnimatedSection>

          <div className="mx-auto mt-16 max-w-5xl 2xl:max-w-[1100px] 3xl:max-w-[1280px]">
            <div className="grid gap-8 md:grid-cols-3">
              {HOW_IT_WORKS.map((step, i) => (
                <AnimatedSection key={step.step} delay={i * 150}>
                  <div className="step-card relative text-center">
                    {/* Step number */}
                    <div className="mb-6 inline-flex items-center justify-center">
                      <div className="relative">
                        <div className={`step-icon-box flex h-20 w-20 items-center justify-center rounded-2xl bg-linear-to-br ${
                          i === 0 ? "from-violet-500 to-purple-500" :
                          i === 1 ? "from-cyan-500 to-blue-500" :
                          "from-emerald-500 to-teal-500"
                        } shadow-lg`}>
                          <step.icon className="h-8 w-8 text-white" />
                        </div>
                        <div className="step-badge absolute -right-2 -top-2 flex h-7 w-7 items-center justify-center rounded-full bg-background text-xs font-bold text-foreground ring-2 ring-border/50">
                          {step.step}
                        </div>
                      </div>
                    </div>

                    {/* Connecting arrow (hidden on last) */}
                    {i < 2 && (
                      <svg className="step-connector pointer-events-none hidden md:block" viewBox="0 0 48 4" aria-hidden="true">
                        <line x1="0" y1="2" x2="48" y2="2" />
                      </svg>
                    )}

                    <h3 className="font-display mb-2 text-lg font-semibold">
                      {step.title}
                    </h3>
                    <p className="mx-auto max-w-xs text-sm leading-relaxed text-muted-foreground">
                      {step.description}
                    </p>
                  </div>
                </AnimatedSection>
              ))}
            </div>
          </div>
        </section>

        {/* ── Section Divider ─────────────────────────── */}
        <div className="section-divider mx-auto max-w-4xl 2xl:max-w-[1000px] 3xl:max-w-[1200px]" />

        {/* ── Features Section ───────────────────────── */}
        <section id="features" className="px-6 py-20 sm:py-28" aria-label="Platform features">
          <AnimatedSection className="mx-auto max-w-3xl text-center">
            <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-primary">
              Platform
            </p>
            <h2 className="font-display mb-4 text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
              Career Intelligence,{" "}
              <span className="gradient-text">Not Career Guesswork</span>
            </h2>
            <p className="mx-auto max-w-xl text-muted-foreground lg:text-lg">
              Six AI-powered modules that work together to understand your
              complete career picture.
            </p>
          </AnimatedSection>

          <div className="mx-auto mt-14 grid max-w-6xl 2xl:max-w-[1200px] 3xl:max-w-[1400px] gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature, i) => (
              <AnimatedSection key={feature.title} delay={i * 80}>
                <SpotlightCard className="glass-card group cursor-default rounded-xl p-6 h-full">
                  <div
                    className={`icon-glow relative z-10 mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-linear-to-br ${feature.gradient} shadow-lg transition-transform duration-300 group-hover:scale-110`}
                    style={{
                      boxShadow: "0 4px 14px oklch(0 0 0 / 25%)",
                    }}
                  >
                    <feature.icon className="h-5 w-5 text-white" />
                  </div>
                  <h3 className="relative z-10 font-display mb-2 text-base font-semibold">
                    {feature.title}
                  </h3>
                  <p className="relative z-10 text-sm leading-relaxed text-muted-foreground">
                    {feature.description}
                  </p>
                </SpotlightCard>
              </AnimatedSection>
            ))}
          </div>
        </section>

        {/* ── Section Divider ─────────────────────────── */}
        <div className="section-divider mx-auto max-w-4xl 2xl:max-w-[1000px] 3xl:max-w-[1200px]" />

        {/* ── Career DNA™ Section ────────────────────── */}
        <section className="px-6 py-20 sm:py-28" aria-label="Career DNA technology">
          <div className="mx-auto max-w-6xl 2xl:max-w-[1200px] 3xl:max-w-[1400px]">
            <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
              {/* Left — Career DNA visualization */}
              <AnimatedSection>
                <div className="elevated-card overflow-hidden rounded-2xl p-6 sm:p-8">
                  <div className="mb-6 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-linear-to-br from-primary to-accent">
                        <Dna className="h-4 w-4 text-white" />
                      </div>
                      <div>
                        <p className="font-display text-sm font-semibold">
                          Career DNA™
                        </p>
                        <p className="text-[11px] text-muted-foreground">
                          Senior Frontend Engineer
                        </p>
                      </div>
                    </div>
                    <div className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-medium text-emerald-400">
                      Active
                    </div>
                  </div>

                  {/* Visual bars */}
                  <div className="space-y-4">
                    {DNA_CAPABILITIES.map((cap, i) => (
                      <div key={cap.label}>
                        <div className="mb-1.5 flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">
                            {cap.label}
                          </span>
                          <span className="font-display font-semibold">
                            {cap.value}
                          </span>
                        </div>
                        <AnimatedBar
                          targetWidth={cap.width}
                          colorClass={cap.color}
                          delay={i * 150}
                        />
                      </div>
                    ))}
                  </div>

                  {/* Next move suggestion */}
                  <div className="next-move-card group mt-6 cursor-pointer rounded-xl p-4 transition-all duration-300">
                    <p className="relative z-10 text-[11px] font-medium uppercase tracking-wider text-muted-foreground/70">
                      Recommended Next Move
                    </p>
                    <div className="relative z-10 mt-2 flex items-center justify-between">
                      <div>
                        <p className="font-display font-semibold">
                          Staff Engineer
                        </p>
                        <p className="text-xs text-muted-foreground">
                          87% confidence · 8-14 months
                        </p>
                      </div>
                      <ChevronRight className="h-4 w-4 text-muted-foreground/50 transition-all duration-300 group-hover:translate-x-1 group-hover:text-primary" />
                    </div>
                  </div>
                </div>
              </AnimatedSection>

              {/* Right — copy */}
              <AnimatedSection delay={200}>
                <div className="mb-3 flex items-center gap-2">
                  <Dna className="h-4 w-4 text-primary" />
                  <p className="text-sm font-semibold uppercase tracking-widest text-primary">
                    Core Technology
                  </p>
                </div>
                <h2 className="font-display mb-6 text-3xl font-bold tracking-tight sm:text-4xl">
                  Your Career DNA™
                </h2>
                <p className="mb-6 max-w-lg text-base leading-relaxed text-muted-foreground lg:text-lg">
                  Like biological DNA encodes your physical traits, Career DNA™
                  encodes your professional identity — skills, experiences,
                  growth patterns, values, and market positioning — into a
                  semantic model that evolves with you.
                </p>
                <ul className="space-y-3">
                  {[
                    "Semantic skill mapping beyond keywords",
                    "Career trajectory pattern recognition",
                    "Market position & growth potential scoring",
                    "AI-disruption vulnerability analysis",
                  ].map((item) => (
                    <li key={item} className="dna-list-item flex items-center gap-3 text-sm">
                      <div className="dna-icon flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10">
                        <ArrowRight className="h-3 w-3 text-primary" />
                      </div>
                      <span className="text-muted-foreground">{item}</span>
                    </li>
                  ))}
                </ul>
              </AnimatedSection>
            </div>
          </div>
        </section>

        {/* ── Section Divider ─────────────────────────── */}
        <div className="section-divider mx-auto max-w-4xl 2xl:max-w-[1000px] 3xl:max-w-[1200px]" />

        {/* ── Pricing ────────────────────────────────── */}
        <section id="pricing" className="px-6 py-20 sm:py-28" aria-label="Pricing plans">
          <AnimatedSection className="mx-auto max-w-3xl text-center">
            <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-primary">
              Pricing
            </p>
            <h2 className="font-display mb-4 text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
              Simple,{" "}
              <span className="gradient-text">Transparent Pricing</span>
            </h2>
            <p className="mx-auto max-w-xl text-muted-foreground lg:text-lg">
              Start free. Upgrade when you&apos;re ready. No hidden fees, no surprises.
            </p>
          </AnimatedSection>

          {/* Pricing Cards */}
          <AnimatedSection delay={200} className="mt-14">
            <PricingCards />
          </AnimatedSection>

          {/* Comparison Table */}
          <AnimatedSection delay={400} className="mt-20">
            <div className="mx-auto max-w-3xl text-center">
              <h3 className="font-display mb-2 text-xl font-bold sm:text-2xl">
                How We Compare
              </h3>
              <p className="mb-10 text-sm text-muted-foreground">
                See how PathForge stacks up against existing career tools.
              </p>
            </div>
            <div className="mx-auto max-w-4xl 2xl:max-w-[1000px] 3xl:max-w-[1200px] overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/30">
                    {COMPARISON.headers.map((header, i) => (
                      <th
                        key={header || "feature"}
                        className={`px-4 py-4 font-display font-semibold ${
                          i === 4
                            ? "text-center text-primary pathforge-column-header pathforge-column-cell"
                            : i === 0
                              ? "text-left text-muted-foreground"
                              : "text-center text-muted-foreground/70"
                        }`}
                      >
                        <span>{header}</span>
                        {i > 0 && (
                          <span
                            className={`mt-1 block text-xs font-normal ${
                              i === 4 ? "text-primary/70" : "text-muted-foreground/50"
                            }`}
                          >
                            {COMPARISON.prices[i - 1]}
                          </span>
                        )}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {COMPARISON.rows.map((row) => (
                    <tr
                      key={row.feature}
                      className="comparison-row border-b border-border/10"
                    >
                      <td className="px-4 py-3.5 font-medium">{row.feature}</td>
                      {row.values.map((val, i) => (
                        <td key={i} className={`px-4 py-3.5 text-center ${i === 3 ? "pathforge-column-cell" : ""}`}>
                          {val ? (
                            <Check
                              className={`mx-auto h-4 w-4 ${
                                i === 3 ? "pathforge-check text-emerald-400" : "text-muted-foreground/50"
                              }`}
                            />
                          ) : (
                            <X className="mx-auto h-4 w-4 text-muted-foreground/20" />
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </AnimatedSection>
        </section>

        {/* ── Section Divider ─────────────────────────── */}
        <div className="section-divider mx-auto max-w-4xl 2xl:max-w-[1000px] 3xl:max-w-[1200px]" />

        {/* ── Testimonials Section ────────────────────── */}
        <section className="py-20 sm:py-28" aria-label="What people say">
          <AnimatedSection className="mx-auto max-w-3xl px-6 text-center">
            <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-primary">
              Early Believers
            </p>
            <h2 className="font-display mb-4 text-3xl font-bold tracking-tight sm:text-4xl">
              What People Are Saying
            </h2>
            <p className="mx-auto max-w-xl text-sm leading-relaxed text-muted-foreground">
              Builders and engineers who share our vision for the future of career intelligence.
            </p>
          </AnimatedSection>

          <div className="mx-auto mt-14 max-w-7xl px-4 sm:px-6 lg:px-8 2xl:max-w-[1400px] 3xl:max-w-[1600px] 4xl:max-w-[1800px]">
            <TestimonialsMarquee speed="normal">
              {TESTIMONIALS.map((t) => (
                <BorderGlow key={t.name} className="w-[340px] shrink-0 sm:w-[380px]">
                  <div
                    className="group relative flex h-full flex-col overflow-hidden rounded-2xl bg-card/80 p-6 transition-all duration-300 hover:-translate-y-0.5"
                  >
                    {/* Gradient glow line */}
                    {t.featured && (
                      <div className="absolute inset-x-0 top-0 h-px bg-linear-to-r from-transparent via-primary/50 to-transparent" />
                    )}

                    <MessageSquareQuote className="mb-4 h-5 w-5 text-primary/30" />

                    <blockquote className="flex-1 text-sm leading-relaxed text-muted-foreground">
                      &ldquo;{t.quote}&rdquo;
                    </blockquote>

                    <div className="mt-6 flex items-center justify-between border-t border-border/15 pt-5">
                      <div className="flex items-center gap-3">
                        <TestimonialAvatar
                          name={t.name}
                          image={t.image}
                          gradient={t.gradient}
                          size={80}
                        />
                        <div>
                          <p className="text-[13px] font-semibold">{t.name}</p>
                          <p className="text-xs text-muted-foreground/70">
                            {t.role} · {t.company}
                          </p>
                        </div>
                      </div>
                      {/* LinkedIn link */}
                      {t.linkedin && (
                        <a
                          href={t.linkedin}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="rounded-lg p-1.5 text-muted-foreground/40 transition-colors hover:bg-secondary/50 hover:text-primary"
                          aria-label={`View ${t.name} on LinkedIn`}
                        >
                          <Linkedin className="h-6 w-6" />
                        </a>
                      )}
                    </div>
                  </div>
                </BorderGlow>
              ))}
            </TestimonialsMarquee>
          </div>
        </section>

        {/* ── Section Divider ─────────────────────────── */}
        <div className="section-divider mx-auto max-w-4xl 2xl:max-w-[1000px] 3xl:max-w-[1200px]" />

        {/* ── FAQ Section ─────────────────────────────── */}
        <section className="px-6 py-20 sm:py-28" aria-label="Frequently asked questions">
          <AnimatedSection className="mx-auto max-w-3xl text-center">
            <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-primary">
              FAQ
            </p>
            <h2 className="font-display mb-4 text-3xl font-bold tracking-tight sm:text-4xl">
              Common Questions
            </h2>
          </AnimatedSection>

          <AnimatedSection className="mx-auto mt-12 max-w-2xl">
            <FaqAccordion items={FAQ} />
          </AnimatedSection>
        </section>

        {/* ── Section Divider ─────────────────────────── */}
        <div className="section-divider mx-auto max-w-4xl 2xl:max-w-[1000px] 3xl:max-w-[1200px]" />

        {/* ── Final CTA Section ──────────────────────── */}
        <section id="cta" className="noise-overlay relative overflow-hidden px-6 py-20 sm:py-28" aria-label="Join the waitlist">
          <div
            className="cta-aura pointer-events-none absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full"
            style={{
              background:
                "radial-gradient(circle, oklch(0.7 0.2 270 / 12%) 0%, oklch(0.75 0.15 195 / 6%) 50%, transparent 70%)",
            }}
          />
          <AnimatedSection className="relative mx-auto max-w-2xl text-center">
            <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-primary">
              Early Access
            </p>
            <h2 className="font-display mb-4 text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
              Ready to Forge Your Path?
            </h2>
            <p className="mb-10 text-muted-foreground lg:text-lg">
              Join the waitlist and be among the first to experience Career
              Intelligence. Free forever for early adopters.
            </p>
            <WaitlistForm variant="hero" className="mx-auto max-w-md" />
          </AnimatedSection>
        </section>
    </>
  );
}
