# Phase I — Mobile Platform Architecture

> **Architecture Decision Record** | **Classification**: Senior Staff Engineer Reference
> **Version**: 1.0.0 | **Date**: 2026-02-28
> **Sprint**: 31–32 | **Phase**: I — Mobile
> **Status**: ✅ APPROVED — Tier-1 Audit Passed (8.9/10) — 3 Gaps Corrected

---

## 1. Executive Summary

Phase I delivers a **secure, intelligence-focused mobile companion** for PathForge. This is not a scaled-down web clone — it is a purpose-built mobile surface optimized for professional decision-making on the go.

**Mission**: Career intelligence in your pocket — summary-first, action-ready, glanceable.

### 1.1 Sprint Scope

| Sprint | Focus                        | Deliverables                                                                   |
| :----- | :--------------------------- | :----------------------------------------------------------------------------- |
| **31** | Foundation + Upload          | Expo Router, auth flow, typed API client, resume upload (camera + file picker) |
| **32** | Intelligence + Notifications | Career DNA mobile view, push notifications with deep linking                   |

### 1.2 Deferred Items Migrated to Phase I

The following items were deferred from earlier sprints and are **evaluated** for inclusion:

| Item                                  | Origin       | Decision        | Rationale                                               |
| :------------------------------------ | :----------- | :-------------- | :------------------------------------------------------ |
| `@sentry/nextjs` frontend integration | Sprint 30    | ❌ Out of scope | Web-specific; mobile uses `sentry-expo` separately      |
| Visual regression baseline capture    | Sprint 30    | ❌ Out of scope | Web-specific tooling                                    |
| Career Resilience trend line          | Sprint 27 O3 | ❌ Out of scope | Requires charting library decision; deferred to Phase J |
| Target role form                      | Sprint 27 O4 | ❌ Out of scope | Web feature enhancement                                 |
| Workflow drill-down modal             | Sprint 28 R3 | ❌ Out of scope | Web feature enhancement                                 |

> **Decision**: Phase I focuses exclusively on mobile foundation. Web-deferred items remain web-scope and will be addressed in future web sprints.

---

## 2. Market Research & Competitive Analysis

### 2.1 Competitor Mobile Offerings

| Platform      | Mobile App       | Key Features                                             | Auth              | Offline               | Push            | Resume Upload    |
| :------------ | :--------------- | :------------------------------------------------------- | :---------------- | :-------------------- | :-------------- | :--------------- |
| **LinkedIn**  | ✅ Full-featured | Feed, messaging, job search, Easy Apply, notifications   | OAuth + biometric | Partial (cached feed) | ✅ Deep-linked  | ✅ From device   |
| **Indeed**    | ✅ Full-featured | Job search, apply, resume, salary tools, company reviews | Email + Google    | ❌ Minimal            | ✅ Job alerts   | ✅ Camera + file |
| **Glassdoor** | ✅ Full-featured | Reviews, salaries, interviews, job search                | Email + Google    | ❌ None               | ✅ Basic alerts | ❌ Web only      |
| **Huntr**     | ❌ Web only      | Job board, pipeline, notes                               | N/A               | N/A                   | N/A             | N/A              |
| **Teal**      | ❌ Web only      | Resume builder, job tracker                              | N/A               | N/A                   | N/A             | N/A              |
| **Jobscan**   | ❌ Web only      | ATS optimization                                         | N/A               | N/A                   | N/A             | N/A              |
| **Eightfold** | ✅ Enterprise    | Talent intelligence (employer-facing)                    | SSO               | Enterprise            | Enterprise      | Enterprise       |
| **Gloat**     | ✅ Enterprise    | Internal mobility (employer-facing)                      | SSO               | Enterprise            | Enterprise      | N/A              |

### 2.2 Gap Analysis

| Capability                        | Market State                                                     | PathForge Mobile Differentiation                                                |
| :-------------------------------- | :--------------------------------------------------------------- | :------------------------------------------------------------------------------ |
| **Career Intelligence on Mobile** | ❌ No competitor offers individual career intelligence on mobile | 🔥 **First-to-market**: Career DNA, Threat Radar, Salary Intelligence summaries |
| **Resume Upload via Camera**      | Indeed: basic photo upload                                       | 🔥 **Server-side parsing** with progress feedback + MIME validation             |
| **Proactive Career Alerts**       | LinkedIn: job match alerts only                                  | 🔥 **Career Threat Radar™ alerts** with severity tiers + deep linking           |
| **Offline Intelligence**          | No competitor caches career intelligence                         | 🔥 **Cached last-known state** for Career DNA + scores                          |
| **Biometric Auth Guard**          | LinkedIn: optional biometric                                     | 🔥 **Secure token storage** via `expo-secure-store` + biometric unlock option   |

### 2.3 Enhancement Strategy

PathForge Mobile is **not** a job search app. It is a **career intelligence companion**:

1. **Summary-first design** — Glanceable scores, not full dashboards
2. **Decision-ready** — Every screen answers "What should I do next?"
3. **Proactive, not reactive** — Push notifications for career threats, not job spam
4. **Intelligence portability** — Your career data, accessible anywhere
5. **Privacy-native** — Secure token storage, no analytics tracking by default

---

## 3. Technical Architecture

### 3.1 Mobile Tech Stack

| Layer           | Technology                                    | Version | Rationale                                         |
| :-------------- | :-------------------------------------------- | :------ | :------------------------------------------------ |
| Framework       | React Native + Expo                           | SDK 52  | Managed workflow, OTA updates, monorepo-friendly  |
| Navigation      | Expo Router v4                                | Latest  | File-based routing, web mental model parity       |
| State           | TanStack Query v5 + React Context             | Latest  | Server state (same as web), minimal shared logic  |
| Secure Storage  | `expo-secure-store`                           | Latest  | Keychain (iOS) / Keystore (Android) for tokens    |
| General Storage | `@react-native-async-storage/async-storage`   | Latest  | Non-sensitive cached state                        |
| HTTP            | Built-in `fetch` + custom client              | N/A     | Mobile-specific with timeouts + offline detection |
| Push            | `expo-notifications`                          | Latest  | Managed push token lifecycle                      |
| Camera/File     | `expo-image-picker` + `expo-document-picker`  | Latest  | Resume capture and upload                         |
| Crash Reporting | `sentry-expo`                                 | Latest  | Crash boundaries, release tagging                 |
| UI              | Custom components + `react-native-reanimated` | Latest  | GPU-accelerated animations, platform-native feel  |

### 3.2 Monorepo Integration

```
pathforge/
├── apps/
│   ├── web/                    # Next.js (existing)
│   ├── api/                    # FastAPI (existing)
│   └── mobile/                 # NEW — Expo app
│       ├── app/                # Expo Router file-based routes
│       │   ├── (auth)/         # Auth screens (login, register)
│       │   ├── (tabs)/         # Main tab navigator
│       │   │   ├── home/       # Career DNA summary home
│       │   │   ├── upload/     # Resume upload
│       │   │   └── settings/   # Profile + notifications
│       │   ├── _layout.tsx     # Root layout with auth guard
│       │   └── +not-found.tsx  # 404 handler
│       ├── components/         # RN-specific components
│       ├── lib/                # Mobile HTTP client, token manager
│       ├── hooks/              # Mobile-specific hooks
│       ├── constants/          # Theme tokens, config
│       ├── assets/             # Images, fonts
│       ├── app.json            # Expo config
│       ├── package.json
│       └── tsconfig.json
├── packages/
│   └── shared/                 # Shared TS types (existing)
│       └── src/
│           └── types/          # API types shared across web + mobile
```

### 3.3 Code Sharing Strategy

| Asset                     | Location          | Shared?                      | Notes                                                                        |
| :------------------------ | :---------------- | :--------------------------- | :--------------------------------------------------------------------------- |
| API Types (`types/api/*`) | `packages/shared` | ✅ Extracted from `apps/web` | 22 type files become platform-agnostic                                       |
| Query Keys                | Per-app           | ❌ Copied                    | Same structure, different import paths                                       |
| HTTP Client               | Per-app           | ❌ Separate                  | Web uses `fetch` + localStorage; mobile uses `fetch` + `expo-secure-store`   |
| Auth Provider             | Per-app           | ❌ Separate                  | Web uses `useReducer` + localStorage; mobile uses `useReducer` + SecureStore |
| API Client modules        | Per-app           | ❌ Separate                  | Import from different HTTP layers                                            |
| Hooks                     | Per-app           | ❌ Separate                  | Platform-specific optimizations                                              |
| Components                | Per-app           | ❌ Completely different      | React DOM vs React Native                                                    |

> **ADR-031-01**: We deliberately avoid a shared HTTP/auth layer. The abstraction cost exceeds the duplication cost at this stage. Mobile has fundamentally different needs (timeouts, offline detection, SecureStore, background refresh). A shared `packages/api-client` can be evaluated post-Phase I if patterns converge.

### 3.4 Type Extraction Plan

The 22 API type files in `apps/web/src/types/api/` will be **moved** to `packages/shared/src/types/api/` and re-exported. Both `apps/web` and `apps/mobile` will import from `@pathforge/shared/types/api`.

This is the **only architectural change to the web app** in Phase I.

---

## 4. Feature Specifications

### 4.1 Auth Flow (Sprint 31)

#### Architecture

```
┌─────────────────────────────────────────────────┐
│                   App Start                      │
│                                                  │
│  ┌────────────┐    Token in     ┌─────────────┐ │
│  │ Check      │──SecureStore──▶│ Validate    │ │
│  │ SecureStore │    found        │ /auth/me    │ │
│  └─────┬──────┘                 └──────┬──────┘ │
│        │ No token                      │        │
│        ▼                               │        │
│  ┌────────────┐                 ┌──────▼──────┐ │
│  │ (auth)/    │                 │ 200: Go to  │ │
│  │ login      │                 │ (tabs)/home │ │
│  │ screen     │                 │             │ │
│  └────────────┘                 │ 401: Refresh│ │
│                                 │ → retry     │ │
│                                 │ → or login  │ │
│                                 └─────────────┘ │
└─────────────────────────────────────────────────┘
```

#### Requirements

- **Deterministic cold start**: Root `_layout.tsx` checks `expo-secure-store` for tokens before rendering any route
- **Secure storage**: Access + refresh tokens stored in `expo-secure-store` (Keychain/Keystore), never in AsyncStorage
- **Background refresh**: When app returns from background (`AppState` listener), validate token freshness
- **Single-flight refresh**: Reuse web's refresh queue pattern — prevent concurrent refresh calls
- **Clear unauthorized state**: On failed refresh, clear SecureStore, navigate to `/(auth)/login`
- **No Turnstile**: Mobile does not use Cloudflare Turnstile (web-only anti-bot); mobile uses device attestation in future if needed

#### Auth State Machine (Same as Web)

```
idle → loading → authenticated | unauthenticated
                ↕ (on 401 or logout)
```

### 4.2 Mobile API Client (Sprint 31)

#### Requirements

- **Typed HTTP client**: `fetchWithAuth<T>()` pattern matching web, but with mobile-specific concerns
- **Timeouts**: 15s default, 30s for upload endpoints, configurable per-request
- **Offline detection**: `NetInfo` check before every request; queue or show offline UI
- **Retry logic**: 1 retry on 5xx, exponential backoff (1s, 2s), no retry on 4xx
- **API base URL**: From `app.json` extra config or environment variable, not `process.env`
- **Error surfacing**: Structured `ApiError` class matching web contract
- **AbortController**: Support request cancellation (e.g., on screen unmount)

#### Offline Strategy

| State                    | Behavior                                        |
| :----------------------- | :---------------------------------------------- |
| **Online**               | Normal API calls                                |
| **Offline, cached data** | Show last-known data with "Offline" banner      |
| **Offline, no cache**    | Show empty state with "Connect to load" message |
| **Transitioning**        | Auto-retry pending requests on reconnection     |

### 4.3 Resume Upload (Sprint 31)

#### Flow

```
┌─────────────┐    ┌──────────────┐    ┌───────────────┐
│ Choose       │    │ Validate     │    │ Upload with   │
│ Source       │───▶│ File         │───▶│ Progress      │
│              │    │              │    │               │
│ • Camera     │    │ • Size ≤10MB │    │ • Multipart   │
│ • Photo Lib  │    │ • MIME check │    │ • Progress %  │
│ • Files      │    │ • Extension  │    │ • Cancel btn  │
└─────────────┘    └──────────────┘    └───────┬───────┘
                                               │
                                        ┌──────▼──────┐
                                        │ Parse +     │
                                        │ Generate    │
                                        │ Career DNA  │
                                        └─────────────┘
```

#### Requirements

- **Three source options**: Camera capture, photo library selection, document picker (files)
- **Client-side validation**: File size ≤ 10MB, allowed MIME types (`application/pdf`, `application/msword`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `text/plain`, `image/jpeg`, `image/png`)
- **Permission flow**: Request camera/media permissions gracefully; show settings redirect if denied
- **Upload progress**: Real-time percentage via `XMLHttpRequest` (not fetch, which lacks progress events)
- **Multipart form data**: Compatible with existing backend `/api/v1/resume/upload` endpoint
- **Cancel support**: `AbortController` to cancel in-flight uploads
- **Server-side parsing**: Leverage existing PDF/DOCX parser (Sprint 29) — no new backend changes needed
- **Image-to-document**: Camera capture sends image for OCR processing on server (future enhancement, Sprint 32+)

### 4.4 Career DNA Mobile View (Sprint 32)

#### Design Philosophy

**Summary-first, not dashboard-first.** The mobile Career DNA view is a **glanceable intelligence card** — not a recreation of the web dashboard.

#### Information Hierarchy

```
┌─────────────────────────────────────────────┐
│  Career DNA Summary                          │
│  ─────────────────                           │
│  Overall Score: 78/100        [█████████░]   │
│  Last Updated: 2h ago                        │
│                                              │
│  ┌─────────────────────────────────────────┐ │
│  │ 🛡️ Career Resilience    72  [████░░]    │ │
│  │ 💰 Salary Position      85  [████████]  │ │
│  │ ⚡ Skill Velocity       64  [████░░░]   │ │
│  │ 🔮 Forecast Index       71  [████░░]    │ │
│  └─────────────────────────────────────────┘ │
│                                              │
│  ▼ Expand: Skill Genome (tap)                │
│  ▼ Expand: Growth Vector (tap)               │
│  ▼ Expand: Market Position (tap)             │
│                                              │
│  ⚠️ 2 Active Threats                         │
│  ┌─────────────────────────────────────────┐ │
│  │ 🔴 High: AI automation risk for ...     │ │
│  │ 🟡 Med: Skill freshness declining ...   │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

#### Requirements

- **Summary card**: Overall Career Vitals score, 4 key metrics with progress bars
- **Expandable blocks**: Tap-to-expand for each Career DNA dimension (no navigation)
- **Threat summary**: Top 3 active threats with severity badges, tap to expand
- **Pull-to-refresh**: Standard mobile pattern for data refresh
- **Skeleton loading**: Animated placeholders during data fetch
- **Cached display**: Show last-known data from AsyncStorage while refreshing
- **No radar chart on mobile**: The SVG hexagonal chart is too complex for small screens; use linear progress bars instead

### 4.5 Push Notifications (Sprint 32)

#### Architecture

```
┌──────────┐     ┌────────────┐     ┌──────────────┐
│ Mobile   │     │ Backend    │     │ Push Service  │
│ App      │────▶│ API        │────▶│ (APNS/FCM)   │
│          │     │            │     │               │
│ Register │     │ Store push │     │ Deliver       │
│ token    │     │ token +    │     │ notification  │
│          │     │ preferences│     │               │
└──────────┘     └────────────┘     └──────────────┘
```

#### Requirements

- **Explicit opt-in**: Never request push permission on first launch; show explanation screen first
- **Permission flow**: "Enable Career Alerts" → system prompt → handle granted/denied/undetermined
- **Token registration**: Send Expo push token to backend via `POST /api/v1/notifications/push-token`
- **Notification taxonomy**: Map to existing notification categories (career_threat, skill_decay, salary_change, opportunity, action_due)
- **Deep linking**: Tapping a notification navigates to the relevant screen (e.g., threat alert → Career DNA threats section)
- **Badge count**: Update app badge with unread notification count
- **Quiet hours**: Respect user's notification preferences from backend settings
- **No spam**: Maximum 3 push notifications per day (configurable server-side)
- **Environment credentials**: Use Expo's push notification service (no direct APNS/FCM setup needed in managed workflow)

#### Backend Changes Required

```python
# NEW endpoint: POST /api/v1/notifications/push-token
# Body: { "token": "ExponentPushToken[xxx]", "platform": "ios" | "android" }
# Stores push token associated with user

# NEW endpoint: DELETE /api/v1/notifications/push-token
# Removes push token on logout

# MODIFY: Notification service — add push delivery channel alongside existing in-app notifications
```

### 4.6 Observability (Sprint 31)

#### Requirements

- **sentry-expo**: Crash reporting, JS exception capture, native crash capture
- **Error boundary**: Root-level `ErrorBoundary` component wrapping the app
- **Release tagging**: `sentry-expo` release = `app.json` version + build number
- **API error hook**: `useApiErrorHandler()` — surfaces error toasts for 4xx/5xx
- **No analytics**: No tracking/analytics SDK in Phase I (privacy-first)

---

## 5. File-by-File Implementation Plan

### Sprint 31 — Foundation + Upload

#### 5.1 Shared Package Enhancement

##### [MODIFY] [package.json](file:///d:/ProfesionalDevelopment/AntigravityProjects/pathforge/packages/shared/package.json)

- Add `types/api` export path

##### [RENAME] `packages/shared/src/types/api.ts` → merge into `api/common.ts`

- Existing `api.ts` (4 types: `ApiResponse`, `ApiError`, `PaginatedResponse`, `HealthResponse`) conflicts with new `api/` directory
- Merge these 4 types into `packages/shared/src/types/api/common.ts`

##### [NEW] `packages/shared/src/types/api/*.ts` (22 files)

- Move all 22 type files from `apps/web/src/types/api/` to `packages/shared/src/types/api/`
- Update barrel export in `packages/shared/src/index.ts`

##### [MODIFY] `apps/web/src/types/api/index.ts` → Re-export barrel

- Rewrite barrel to `export type * from "@pathforge/shared/types/api"`
- **Zero changes** to any web component/hook that imports from `@/types/api`
- The barrel absorbs the redirection — lowest-risk migration path

---

#### 5.2 Expo App Scaffold

##### [NEW] `apps/mobile/package.json`

- Dependencies: expo, expo-router, expo-secure-store, expo-image-picker, expo-document-picker, expo-notifications, @tanstack/react-query, sentry-expo, react-native-reanimated, @react-native-async-storage/async-storage, expo-network
- Scripts: `start`, `android`, `ios`, `lint`, `typecheck`, `test`

##### [NEW] `apps/mobile/app.json`

- Expo config: name, slug, scheme, version, orientation, splash, icon, platforms
- Extra config: `apiBaseUrl` from environment

##### [NEW] `apps/mobile/tsconfig.json`

- Extends from root, paths alias for `@pathforge/shared`

##### [NEW] `apps/mobile/babel.config.js`

- Expo preset + reanimated plugin

##### [NEW] `apps/mobile/.env.example`

- `EXPO_PUBLIC_API_URL=http://localhost:8000`
- `SENTRY_DSN=`

---

#### 5.3 Navigation + Auth

##### [NEW] `apps/mobile/app/_layout.tsx`

- Root layout: `<Slot>` with auth guard logic
- Uses `expo-splash-screen` `preventAutoHideAsync()` to hold splash while tokens hydrate from SecureStore (async, unlike web's synchronous localStorage)
- Calls `SplashScreen.hideAsync()` after auth state resolves — prevents flash of login screen
- Wraps app in `QueryProvider` + `AuthProvider`
- Includes `ErrorBoundary` from sentry-expo

##### [NEW] `apps/mobile/app/(auth)/_layout.tsx`

- Stack navigator for auth screens

##### [NEW] `apps/mobile/app/(auth)/login.tsx`

- Email + password login form
- "Create Account" link to register
- Error display + loading states
- Keyboard-avoiding view

##### [NEW] `apps/mobile/app/(auth)/register.tsx`

- Full name + email + password registration
- Password strength indicator
- Terms acceptance checkbox

##### [NEW] `apps/mobile/app/(tabs)/_layout.tsx`

- Bottom tab navigator: Home, Upload, Settings
- Auth-gated (redirects to login if unauthenticated)
- Tab bar icons + labels

##### [NEW] `apps/mobile/app/(tabs)/home/index.tsx`

- Career DNA summary (Sprint 32 wiring)
- Placeholder in Sprint 31

##### [NEW] `apps/mobile/app/(tabs)/upload/index.tsx`

- Resume upload screen (Sprint 31)

##### [NEW] `apps/mobile/app/(tabs)/settings/index.tsx`

- Profile info + logout + notification preferences (Sprint 32 wiring)

##### [NEW] `apps/mobile/app/+not-found.tsx`

- 404 fallback screen

---

#### 5.4 Mobile Core Libraries

##### [NEW] `apps/mobile/lib/token-manager.ts`

- `getAccessToken()`, `getRefreshToken()`, `setTokens()`, `clearTokens()`, `hasTokens()`
- Uses `expo-secure-store` instead of localStorage
- In-memory cache for performance
- No multi-tab sync needed (single app instance)

##### [NEW] `apps/mobile/lib/refresh-queue.ts`

- Single-flight token refresh (same pattern as web)
- Uses mobile token manager imports

##### [NEW] `apps/mobile/lib/http.ts`

- `fetchWithAuth<T>()`, `fetchPublic<T>()`, `get()`, `post()`, `put()`, `patch()`, `del()`
- API base URL from `Constants.expoConfig.extra.apiBaseUrl`
- Request timeout via `AbortController` + `setTimeout` (15s default, 30s uploads)
- Offline detection via `expo-network` `NetInfo`
- `ApiError` class matching web contract

##### [NEW] `apps/mobile/lib/network.ts`

- Network status monitoring hook: `useNetworkStatus()`
- Online/offline state + connection type
- Event listener for connectivity changes

##### [NEW] `apps/mobile/lib/api-client/auth.ts`

- `login()`, `register()`, `logout()`, `refreshToken()`, `getCurrentUser()`

##### [NEW] `apps/mobile/lib/api-client/career-dna.ts`

- Career DNA summary, dimensions, readiness score

##### [NEW] `apps/mobile/lib/api-client/resume.ts`

- `uploadResume()` — multipart upload with progress callback

##### [NEW] `apps/mobile/lib/api-client/notifications.ts`

- Push token registration, preferences, notification list

##### [NEW] `apps/mobile/lib/api-client/health.ts`

- Backend health check

---

#### 5.5 Auth Provider

##### [NEW] `apps/mobile/providers/auth-provider.tsx`

- Same `useReducer` 4-state machine as web
- Uses mobile `token-manager.ts` (SecureStore)
- `AppState` listener: validate token on foreground return
- Session restore from SecureStore on mount

##### [NEW] `apps/mobile/providers/query-provider.tsx`

- TanStack Query v5 client
- Smart retry: skip 4xx, retry 5xx
- 5min stale time (same as web)
- `onlineManager` integration with `expo-network`

---

#### 5.6 Resume Upload Component

##### [NEW] `apps/mobile/components/resume-upload.tsx`

- Three-option source selector (camera, gallery, files)
- Permission request flow with settings redirect
- File validation (size, MIME type)
- Upload progress bar (0-100%)
- Cancel button during upload
- Success → navigate to Career DNA generation
- Error handling with retry option

##### [NEW] `apps/mobile/hooks/use-resume-upload.ts`

- `pickFromCamera()`, `pickFromGallery()`, `pickFromFiles()`
- `uploadResume()` with progress tracking
- Permission management
- State: idle, picking, validating, uploading, success, error

---

#### 5.7 Shared UI Components

##### [NEW] `apps/mobile/components/ui/button.tsx`

- Pressable with haptic feedback, loading state, variants (primary/secondary/ghost)

##### [NEW] `apps/mobile/components/ui/input.tsx`

- TextInput with label, error state, focus styling

##### [NEW] `apps/mobile/components/ui/score-bar.tsx`

- Horizontal progress bar for scores (0-100), 4-tier coloring

##### [NEW] `apps/mobile/components/ui/card.tsx`

- Container card with shadow, rounded corners

##### [NEW] `apps/mobile/components/ui/skeleton.tsx`

- Animated skeleton loading placeholder

##### [NEW] `apps/mobile/components/ui/toast.tsx`

- Toast notification for API errors, success messages

##### [NEW] `apps/mobile/components/ui/offline-banner.tsx`

- Persistent banner showing offline state

##### [NEW] `apps/mobile/components/error-boundary.tsx`

- Sentry-integrated error boundary with fallback UI

---

#### 5.8 Constants + Theme

##### [NEW] `apps/mobile/constants/theme.ts`

- Color tokens (matching web brand), spacing scale, typography scale
- Light + dark mode support

##### [NEW] `apps/mobile/constants/config.ts`

- API timeouts, retry config, file upload limits, notification caps

---

### Sprint 32 — Intelligence + Notifications

#### 5.9 Career DNA Mobile View

##### [NEW] `apps/mobile/hooks/api/use-career-dna.ts`

- TanStack Query hooks for Career DNA summary, dimensions, readiness
- Auth-gated queries
- Cached display support via AsyncStorage

##### [NEW] `apps/mobile/hooks/api/use-command-center.ts`

- Career Vitals score, engine status

##### [NEW] `apps/mobile/hooks/api/use-threat-radar.ts`

- Top threats, resilience score

##### [NEW] `apps/mobile/components/career-dna-summary.tsx`

- Overall score with circular progress indicator
- 4 key metric bars (Resilience, Salary, Velocity, Forecast)
- "Last updated" timestamp

##### [NEW] `apps/mobile/components/expandable-intelligence-block.tsx`

- Tap-to-expand section for each Career DNA dimension
- Animated expand/collapse with `react-native-reanimated`

##### [NEW] `apps/mobile/components/threat-summary.tsx`

- Top 3 threats with severity badges
- Tap to expand each threat for details + opportunity

##### [MODIFY] `apps/mobile/app/(tabs)/home/index.tsx`

- Wire Career DNA summary + threat summary
- Pull-to-refresh
- Skeleton loading states

---

#### 5.10 Push Notifications

##### [NEW] `apps/mobile/hooks/use-push-notifications.ts`

- Permission request flow
- Expo push token registration
- Notification received handler (foreground)
- Notification response handler (deep link navigation)
- Token refresh on app activation

##### [NEW] `apps/mobile/components/notification-opt-in.tsx`

- Explanation screen: what notifications you'll receive
- "Enable Career Alerts" button
- "Not Now" skip option

##### [MODIFY] `apps/mobile/app/(tabs)/settings/index.tsx`

- Notification preferences toggle
- Push permission status display
- Profile info + logout

##### Backend Changes:

##### [MODIFY] `apps/api/app/api/v1/notifications.py`

- Add push token endpoints to **existing** notification router (not a separate router)
- `POST /api/v1/notifications/push-token` — register Expo push token
- `DELETE /api/v1/notifications/push-token` — deregister on logout
- `GET /api/v1/notifications/push-status` — check push registration status

##### [NEW] `apps/api/app/models/push_token.py`

- `PushToken` model: `id`, `user_id`, `token`, `platform`, `created_at`, `updated_at`

##### [MODIFY] `apps/api/app/models/notification.py`

- Add `push_notifications: bool` field to `NotificationPreference` model (parallels existing `email_notifications` field)

##### [NEW] `apps/api/app/schemas/push_notification.py`

- Pydantic schemas for push token registration

##### [MODIFY] `apps/api/app/services/notification_service.py`

- Extend `emit_notification()` to check `push_notifications` preference before dispatching
- Add push delivery channel using Expo Push API
- Respect notification preferences

##### [NEW] Alembic migration for `push_tokens` table + `push_notifications` column on `notification_preferences`

##### [MODIFY] `.github/workflows/ci.yml`

- Add `mobile` path filter to `dorny/paths-filter`
- Add `mobile-quality` job: lint, typecheck, test for `apps/mobile/`

##### [MODIFY] Root `package.json`

- Add `dev:mobile` script: `pnpm --filter pathforge-mobile start`

---

## 6. Manual Configuration Guide

### 6.1 Expo Project Setup

```bash
# 1. Create Expo app within monorepo
cd apps/
npx -y create-expo-app@latest mobile --template blank-typescript

# 2. Install dependencies
cd mobile
npx expo install expo-router expo-secure-store expo-image-picker \
  expo-document-picker expo-notifications expo-network \
  react-native-reanimated react-native-safe-area-context \
  react-native-screens @react-native-async-storage/async-storage \
  expo-constants expo-linking expo-status-bar expo-splash-screen

# 3. Install dev dependencies
pnpm add -D @types/react @types/react-native typescript \
  @tanstack/react-query sentry-expo jest @testing-library/react-native
```

### 6.2 Environment Variables

| Variable              | Where                     | Purpose                                         |
| :-------------------- | :------------------------ | :---------------------------------------------- |
| `EXPO_PUBLIC_API_URL` | `.env` / `app.json` extra | Backend API base URL                            |
| `SENTRY_DSN`          | `app.json` extra          | Sentry error tracking (mobile-specific project) |
| `EXPO_PROJECT_ID`     | `app.json` extra          | EAS Build project identifier                    |

### 6.3 Apple Developer Console (Future — Pre-Store)

> Not needed for development builds. Required before App Store submission.

1. Create App ID with Push Notifications capability
2. Generate APNs key (.p8) for push notifications
3. Upload APNs key to Expo dashboard
4. Configure bundle identifier in `app.json`

### 6.4 Google Play Console (Future — Pre-Store)

> Not needed for development builds. Required before Play Store submission.

1. Create app in Google Play Console
2. Firebase Cloud Messaging (FCM) server key configured via Expo dashboard
3. Configure package name in `app.json`

### 6.5 Expo Push Notifications Setup

```bash
# Expo manages APNS/FCM credentials in managed workflow
# No direct APNS/FCM setup needed for development

# 1. Register project with Expo push service
npx expo install expo-notifications

# 2. For production: run EAS credential setup
eas credentials
```

### 6.6 Validation Steps

1. ✅ `pnpm install` succeeds from monorepo root
2. ✅ `pnpm --filter pathforge-mobile start` launches Expo dev server
3. ✅ TypeScript compilation: `pnpm --filter pathforge-mobile typecheck`
4. ✅ Login flow works on iOS Simulator / Android Emulator
5. ✅ Resume upload completes with progress feedback
6. ✅ Push notification permission flow completes
7. ✅ Deep link from notification navigates correctly

### 6.7 Rollback Instructions

- **Remove mobile app**: Delete `apps/mobile/` directory, remove from `pnpm-workspace.yaml` if added
- **Revert shared types**: The type extraction is backward-compatible; web re-exports from shared
- **Backend push endpoints**: New endpoints are additive; removal is safe (no existing consumers)

---

## 7. Ethics, Privacy & Safety Assessment

| Risk                         | Severity | Probability | Mitigation                                                                                |
| :--------------------------- | :------- | :---------- | :---------------------------------------------------------------------------------------- |
| **Token storage insecurity** | Critical | Low         | `expo-secure-store` uses Keychain (iOS) / Keystore (Android) — hardware-backed encryption |
| **Camera permission abuse**  | Medium   | Low         | Permission requested only on user action; clear explanation UI; graceful denial handling  |
| **Push notification spam**   | Medium   | Medium      | Explicit opt-in, category-based preferences, 3/day cap, quiet hours respect               |
| **Offline data staleness**   | Low      | Medium      | "Last updated" timestamp on all cached data; stale data banner                            |
| **Resume data on device**    | Medium   | Low         | Resume content not stored locally; only upload + server-side processing                   |
| **GDPR mobile compliance**   | High     | Low         | Same data handling as web; no additional data collection on mobile                        |

---

## 8. Verification Plan

### 8.1 Automated Tests

```bash
# Mobile unit tests (Jest + React Native Testing Library)
cd apps/mobile
pnpm test

# Expected test suites:
# - lib/token-manager.test.ts (8 tests — get/set/clear/has)
# - lib/http.test.ts (12 tests — fetchWithAuth, timeout, offline, retry)
# - lib/network.test.ts (5 tests — online/offline detection)
# - hooks/use-resume-upload.test.ts (8 tests — pick/validate/upload/cancel)
# - hooks/use-push-notifications.test.ts (6 tests — permission/register/handle)
# - components/resume-upload.test.tsx (6 tests — render/interaction/validation)
# - providers/auth-provider.test.tsx (10 tests — reducer/login/logout/restore)
# Total: ~55 tests across Sprint 31-32
```

```bash
# Backend tests (Sprint 32 push endpoints)
cd apps/api
python -m pytest tests/test_push_notifications.py -v
# Expected: ~8 tests for push token CRUD
```

```bash
# Web regression (ensure type extraction didn't break anything)
cd apps/web
pnpm test          # 232/232 tests must pass
pnpm typecheck     # 0 errors
pnpm build         # Production build passes
```

```bash
# Full monorepo checks
pnpm -r lint       # 0 errors across all packages
pnpm -r typecheck  # 0 errors across all packages
```

### 8.2 Manual Verification

| Test                   | Platform      | Steps                                                       | Expected Result                                   |
| :--------------------- | :------------ | :---------------------------------------------------------- | :------------------------------------------------ |
| Cold start auth        | iOS + Android | 1. Kill app 2. Reopen 3. Should auto-login if tokens valid  | Home screen with Career DNA (or login if expired) |
| Login flow             | iOS + Android | 1. Enter email/password 2. Tap Login 3. Check SecureStore   | Navigates to home, tokens in SecureStore          |
| Logout                 | iOS + Android | 1. Settings → Logout 2. Check SecureStore                   | Navigates to login, tokens cleared                |
| Resume upload (camera) | iOS + Android | 1. Tap Upload tab 2. Choose Camera 3. Take photo 4. Confirm | Upload progress shown, success message            |
| Resume upload (file)   | iOS + Android | 1. Tap Upload tab 2. Choose Files 3. Select PDF 4. Wait     | Upload progress, parsing begins                   |
| Offline behavior       | iOS + Android | 1. Enable airplane mode 2. Open app 3. Try actions          | Offline banner shown, cached data displayed       |
| Push opt-in            | iOS + Android | 1. Settings → Enable Alerts 2. Accept permission            | Push token registered, toggle shows enabled       |
| Deep link notification | iOS + Android | 1. Receive push 2. Tap notification                         | Navigates to relevant Career DNA section          |

---

## 9. Sprint Velocity Estimates

| Sprint    | New Files | Modified Files              | Tests (Mobile) | Tests (Backend) | Sessions |
| :-------- | :-------- | :-------------------------- | :------------- | :-------------- | :------- |
| 31        | ~25       | ~5 (web type re-exports)    | ~35            | 0               | 2–3      |
| 32        | ~10       | ~3 (backend push endpoints) | ~20            | ~8              | 1–2      |
| **Total** | **~35**   | **~8**                      | **~55**        | **~8**          | **3–5**  |

---

## 10. Success Metrics

| Metric                     | Target       | Measurement                |
| :------------------------- | :----------- | :------------------------- |
| Cold start to interactive  | < 3 seconds  | Manual profiling           |
| Login → home screen        | < 2 seconds  | API latency + render       |
| Resume upload (5MB PDF)    | < 10 seconds | End-to-end timing          |
| Career DNA load (cached)   | < 500ms      | AsyncStorage read + render |
| Push notification delivery | < 30 seconds | Server → device latency    |
| Crash-free sessions        | > 99.5%      | Sentry monitoring          |
| Mobile test count          | ≥ 55         | CI pipeline                |
