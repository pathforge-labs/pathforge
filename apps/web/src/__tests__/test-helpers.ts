/**
 * PathForge — Test Helpers
 * =========================
 * Shared test utilities for mocking fetch and building responses.
 * Auto-loaded via vitest.config.mts setupFiles.
 */

import { afterEach, vi } from "vitest";

// ── Auto-cleanup ────────────────────────────────────────────

afterEach(() => {
  vi.restoreAllMocks();
});

// ── Fetch Mock Utilities ────────────────────────────────────

/** Create a mock for `global.fetch` and return the spy. */
export function mockFetch(): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** Build a successful Response-like object. */
export function mockFetchResponse<TData>(
  data: TData,
  status: number = 200,
): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
    headers: new Headers(),
    redirected: false,
    type: "basic" as ResponseType,
    url: "",
    clone: () => mockFetchResponse(data, status),
    body: null,
    bodyUsed: false,
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    blob: () => Promise.resolve(new Blob()),
    formData: () => Promise.resolve(new FormData()),
    bytes: () => Promise.resolve(new Uint8Array()),
  } as Response;
}

/** Build a 204 No Content response. */
export function mockNoContentResponse(): Response {
  return mockFetchResponse(null, 204);
}

/** Build an error response matching FastAPI format. */
export function mockErrorResponse(
  status: number,
  detail: string,
  errorCode?: string,
): Response {
  const body: Record<string, unknown> = { detail };
  if (errorCode) body["error_code"] = errorCode;
  return {
    ok: false,
    status,
    statusText: "Error",
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
    headers: new Headers(),
    redirected: false,
    type: "basic" as ResponseType,
    url: "",
    clone: () => mockErrorResponse(status, detail, errorCode),
    body: null,
    bodyUsed: false,
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    blob: () => Promise.resolve(new Blob()),
    formData: () => Promise.resolve(new FormData()),
    bytes: () => Promise.resolve(new Uint8Array()),
  } as Response;
}

// ── localStorage Mock ───────────────────────────────────────

/** Create an in-memory localStorage mock for token tests. */
export function mockLocalStorage(): Storage {
  const store = new Map<string, string>();
  return {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => { store.set(key, value); },
    removeItem: (key: string) => { store.delete(key); },
    clear: () => { store.clear(); },
    get length() { return store.size; },
    key: (index: number) => [...store.keys()][index] ?? null,
  };
}
