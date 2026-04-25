# PathForge — Mobile App Launch Plan

> **Sprint 44 P2-4 deliverable.**
> Current state: Expo SDK 52 + Expo Router; auth flow, API client, resume upload,
> Career DNA view, push notifications, 69 tests (7 suites). Sentry integrated.
>
> This document covers the path from local Expo Go to App Store + Google Play.

---

## Phase 1 — Pre-submission (requires OPS-3 + OPS-4)

**Blockers before any build:**
- OPS-3: `ANTHROPIC_API_KEY`, `GOOGLE_AI_API_KEY`, `VOYAGE_API_KEY` → LLM features work
- OPS-4: Redis live → push notification dedup, rate limiting

**Tasks:**
- [ ] Set `EXPO_PUBLIC_API_URL=https://api.pathforge.eu` in `apps/mobile/.env.production`
- [ ] Verify push notification flow end-to-end on physical device
- [ ] Run full smoke test on iOS Simulator + Android Emulator
  - Register → Verify → Login → Upload CV → Career DNA → Logout
- [ ] Confirm Sentry `@sentry/react-native` captures errors (set `SENTRY_DSN` in Expo env)
- [ ] Check all `console.log` removed from production bundle (CI hook already enforces this)

---

## Phase 2 — EAS Build setup

**Install EAS CLI:**
```bash
npm install -g eas-cli
eas login  # Expo account required
```

**Configure `eas.json`** (create in `apps/mobile/`):
```json
{
  "cli": { "version": ">= 12.0.0" },
  "build": {
    "production": {
      "ios": { "resourceClass": "m-medium" },
      "android": { "buildType": "apk" }
    },
    "preview": {
      "distribution": "internal",
      "ios": { "simulator": true }
    }
  },
  "submit": {
    "production": {
      "ios": { "appleId": "emre@pathforge.eu", "ascAppId": "<TBD>" },
      "android": { "serviceAccountKeyPath": "./google-service-account.json", "track": "internal" }
    }
  }
}
```

**Build for production:**
```bash
cd apps/mobile
eas build --platform all --profile production
```

---

## Phase 3 — App Store (iOS)

**One-time setup (Apple Developer account — emre@pathforge.eu):**
1. [developer.apple.com](https://developer.apple.com) → Certificates, IDs & Profiles → App IDs → Register `eu.pathforge.app`
2. App Store Connect → New App → fill metadata
3. Add screenshots (6.7" + 5.5" for iPad optional)
4. Privacy policy URL: `https://pathforge.eu/privacy`
5. Review information: demo account `demo@pathforge.eu` / `DemoPassword123!`

**Submit:**
```bash
eas submit --platform ios --latest
```

**Expected review time**: 1–3 business days.

---

## Phase 4 — Google Play (Android)

**One-time setup (Google Play Console):**
1. [play.google.com/console](https://play.google.com/console) → Create app → `eu.pathforge.app`
2. Fill store listing: title, short description (80 chars), full description, screenshots
3. Content rating questionnaire (Career app → likely Everyone)
4. Target API level: Android 14 (API 34) — Expo SDK 52 default
5. Privacy policy: `https://pathforge.eu/privacy`
6. Set up Google Service Account for EAS submit → download `google-service-account.json`

**Submit to Internal Testing first:**
```bash
eas submit --platform android --latest --track internal
```
Promote to Production after 3–5 days of internal testing.

---

## Phase 5 — ASO (App Store Optimisation)

**App name**: PathForge — AI Career Coach  
**Subtitle (iOS)**: Career DNA™ · Job Intelligence  
**Keywords (iOS, 100 chars)**: career,cv,resume,job,ai,salary,skill,coach,interview,pathforge  
**Short description (Android, 80 chars)**: AI-powered career intelligence: Career DNA, job matching, salary insights  

**Screenshots to capture** (must be in CI/Playwright or on device):
- Onboarding / Career DNA generation
- Dashboard with Career Vitals™ score
- Salary Intelligence comparison
- Threat Radar™ alerts

---

## Phase 6 — Phased rollout

| Stage | Platform | Scope | Duration |
| :--- | :--- | :--- | :--- |
| Internal | Both | Team + beta testers (≤25) | 1 week |
| Open beta (TestFlight / Play beta) | Both | Up to 10,000 | 2 weeks |
| Production (phased) | Android | 10% → 50% → 100% | 1 week |
| Production | iOS | Full release | Day of approval |

**Monitoring during rollout:**
- Sentry crash-free sessions rate ≥ 99%
- UptimeRobot `https://api.pathforge.eu/api/v1/health/ready` → green
- App Store Connect / Play Console ANR + crash rate → below 0.47% threshold

---

## Dependencies summary

| Dependency | Needed for | Status |
| :--- | :--- | :--- |
| OPS-3 LLM keys | Career DNA, AI features | ❌ Not provisioned |
| OPS-4 Redis | Push notif dedup, rate limit | ❌ Not provisioned |
| OPS-1 Sentry DSN | Crash reporting | ❌ Not provisioned |
| Apple Developer account | iOS submission | ❌ Needs verification |
| Google Play Console account | Android submission | ❌ Needs verification |
| EAS account | Build service | ❌ Needs setup |
| `eas.json` config | EAS builds | ❌ File not yet created |

---

## Timeline estimate

| Phase | Effort | Elapsed |
| :--- | :--- | :--- |
| OPS-3 + OPS-4 provisioned | 1–2h | Day 0 |
| Phase 1 smoke test | 2–4h | Day 1 |
| Phase 2 EAS setup + first build | 2–3h | Day 1 |
| Phase 3 App Store submission | 2h setup + 1–3 days review | Day 2–5 |
| Phase 4 Play Store submission | 2h setup + up to 7 days review | Day 2–9 |
| Phase 5 ASO + screenshots | 4–8h | Day 2 |
| Phase 6 phased rollout | 2–3 weeks | Day 10–30 |
