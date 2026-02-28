/**
 * PathForge Mobile — Network Monitor
 * =====================================
 * Network connectivity monitoring using expo-network.
 * Provides a React hook and utility functions for offline detection.
 */

import * as Network from "expo-network";
import { useCallback, useEffect, useState } from "react";

// ── Types ───────────────────────────────────────────────────

export interface NetworkStatus {
  /** Whether the device has an active network connection. */
  isConnected: boolean;
  /** Whether the connection has internet access. */
  isInternetReachable: boolean;
  /** Loading state during initial check. */
  isChecking: boolean;
}

// ── Hook ────────────────────────────────────────────────────

/**
 * React hook for monitoring network connectivity.
 *
 * Checks network state on mount and polls periodically.
 * Note: expo-network doesn't support real-time listeners in
 * managed workflow — we use a polling strategy instead.
 */
export function useNetworkStatus(pollIntervalMs: number = 10_000): NetworkStatus {
  const [status, setStatus] = useState<NetworkStatus>({
    isConnected: true,
    isInternetReachable: true,
    isChecking: true,
  });

  const checkNetwork = useCallback(async (): Promise<void> => {
    try {
      const networkState = await Network.getNetworkStateAsync();
      setStatus({
        isConnected: networkState.isConnected ?? false,
        isInternetReachable: networkState.isInternetReachable ?? false,
        isChecking: false,
      });
    } catch {
      setStatus({
        isConnected: false,
        isInternetReachable: false,
        isChecking: false,
      });
    }
  }, []);

  useEffect(() => {
    // Initial check
    void checkNetwork();

    // Poll periodically
    const interval = setInterval(() => {
      void checkNetwork();
    }, pollIntervalMs);

    return () => clearInterval(interval);
  }, [checkNetwork, pollIntervalMs]);

  return status;
}

// ── Utility ─────────────────────────────────────────────────

/**
 * One-shot network check — returns true if online.
 */
export async function isOnline(): Promise<boolean> {
  try {
    const state = await Network.getNetworkStateAsync();
    return (state.isConnected ?? false) && (state.isInternetReachable ?? false);
  } catch {
    return false;
  }
}
