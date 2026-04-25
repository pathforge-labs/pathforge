/**
 * PathForge — Recharts Chart (Inner Component)
 * ================================================
 * Sprint 36 WS-5: Dynamically imported (ssr: false) to avoid hydration mismatch.
 *
 * This file is imported via next/dynamic in resilience-trend.tsx.
 * It must be a default export for next/dynamic compatibility.
 */

"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { ResilienceDataPoint } from "@/hooks/api/use-resilience-trend";

// ── Custom Tooltip ───────────────────────────────────────────

interface TooltipContentProps {
  readonly active?: boolean;
  readonly payload?: readonly { readonly value: number; readonly payload: ResilienceDataPoint }[];
  readonly label?: string;
}

function CustomTooltip({ active, payload, label }: TooltipContentProps) {
  if (!active || !payload?.length) return null;

  const point = payload[0];
  const delta = point.payload.delta;
  const deltaSign = delta >= 0 ? "+" : "";
  const deltaColor = delta >= 0 ? "#4ADE80" : "#F87171";

  return (
    <div
      style={{
        background: "rgba(15, 23, 42, 0.95)",
        border: "1px solid rgba(255, 255, 255, 0.1)",
        borderRadius: "8px",
        padding: "12px 16px",
        fontSize: "13px",
      }}
    >
      <p style={{ color: "#94A3B8", margin: "0 0 4px" }}>{label}</p>
      <p style={{ color: "#F8FAFC", margin: "0 0 2px", fontWeight: 600 }}>
        Score: {point.value}
      </p>
      <p style={{ color: deltaColor, margin: 0 }}>
        {deltaSign}{delta} from previous
      </p>
    </div>
  );
}

// ── Chart Component ──────────────────────────────────────────

interface ChartProps {
  readonly data: readonly ResilienceDataPoint[];
}

export default function ResilienceTrendChart({ data }: ChartProps) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={[...data]} margin={{ top: 8, right: 8, bottom: 8, left: -20 }}>
        <defs>
          <linearGradient id="resilienceGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.2} />
            <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="rgba(255, 255, 255, 0.06)"
          vertical={false}
        />
        <XAxis
          dataKey="date"
          tick={{ fill: "#64748B", fontSize: 11 }}
          axisLine={{ stroke: "rgba(255, 255, 255, 0.06)" }}
          tickLine={false}
          tickFormatter={(value: string) => {
            const date = new Date(value);
            return `${date.getMonth() + 1}/${date.getDate()}`;
          }}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fill: "#64748B", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <Line
          type="monotone"
          dataKey="score"
          stroke="#3B82F6"
          strokeWidth={2.5}
          dot={false}
          activeDot={{
            r: 5,
            fill: "#3B82F6",
            stroke: "#1E293B",
            strokeWidth: 2,
          }}
          fill="url(#resilienceGradient)"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
