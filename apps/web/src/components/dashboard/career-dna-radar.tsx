/**
 * PathForge — Career DNA Radar Chart
 * =====================================
 * Pure SVG hexagonal radar chart visualizing 6 Career DNA dimensions.
 * No external chart library dependency — zero bundle cost.
 *
 * Innovation: No competitor offers individual-owned multi-dimension
 * career visualization. Enterprise tools (Eightfold/Gloat) restrict
 * this to HR dashboards.
 */

"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

/* ── Types ────────────────────────────────────────────────── */

export interface RadarDimension {
  /** Display label for the axis */
  readonly label: string;
  /** Normalized value 0–100 */
  readonly value: number;
  /** Emoji icon for the axis vertex */
  readonly icon: string;
}

export interface CareerDnaRadarProps {
  /** Array of exactly 6 dimensions to plot */
  readonly dimensions: readonly RadarDimension[];
  /** Show skeleton state */
  readonly isLoading?: boolean;
}

/* ── Constants ────────────────────────────────────────────── */

const CENTER_X = 150;
const CENTER_Y = 150;
const MAX_RADIUS = 110;
const RING_COUNT = 4;
const LABEL_OFFSET = 28;

/* ── Geometry Helpers ─────────────────────────────────────── */

function polarToCartesian(
  centerX: number,
  centerY: number,
  radius: number,
  angleInDegrees: number,
): { x: number; y: number } {
  const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180;
  return {
    x: centerX + radius * Math.cos(angleInRadians),
    y: centerY + radius * Math.sin(angleInRadians),
  };
}

function getPolygonPoints(
  dimensions: readonly RadarDimension[],
  maxRadius: number,
): string {
  const angleStep = 360 / dimensions.length;
  return dimensions
    .map((dimension, index) => {
      const radius = (Math.max(0, Math.min(100, dimension.value)) / 100) * maxRadius;
      const point = polarToCartesian(CENTER_X, CENTER_Y, radius, index * angleStep);
      return `${point.x},${point.y}`;
    })
    .join(" ");
}

function getGridPolygonPoints(radius: number, sides: number): string {
  const angleStep = 360 / sides;
  return Array.from({ length: sides }, (_, index) => {
    const point = polarToCartesian(CENTER_X, CENTER_Y, radius, index * angleStep);
    return `${point.x},${point.y}`;
  }).join(" ");
}

/* ── Score color ──────────────────────────────────────────── */

function getAreaGradientId(averageScore: number): string {
  if (averageScore >= 70) return "radarGradientGreen";
  if (averageScore >= 40) return "radarGradientAmber";
  return "radarGradientRed";
}

/* ── Component ────────────────────────────────────────────── */

export function CareerDnaRadar({ dimensions, isLoading = false }: CareerDnaRadarProps) {
  const sides = dimensions.length;
  const angleStep = 360 / sides;
  const averageScore = dimensions.reduce((sum, d) => sum + d.value, 0) / sides;

  return (
    <Card>
      <CardHeader className="text-center pb-2">
        <CardTitle className="text-lg">Career DNA™ Profile</CardTitle>
        <CardDescription>
          Your career shape across 6 dimensions
        </CardDescription>
      </CardHeader>
      <CardContent className="flex justify-center">
        <svg
          viewBox="0 0 300 300"
          className="w-full max-w-[320px]"
          role="img"
          aria-label="Career DNA radar chart showing 6 career dimensions"
        >
          {/* Gradient definitions */}
          <defs>
            <radialGradient id="radarGradientGreen" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="hsl(142 71% 45%)" stopOpacity="0.4" />
              <stop offset="100%" stopColor="hsl(142 71% 45%)" stopOpacity="0.1" />
            </radialGradient>
            <radialGradient id="radarGradientAmber" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="hsl(38 92% 50%)" stopOpacity="0.4" />
              <stop offset="100%" stopColor="hsl(38 92% 50%)" stopOpacity="0.1" />
            </radialGradient>
            <radialGradient id="radarGradientRed" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="hsl(0 84% 60%)" stopOpacity="0.4" />
              <stop offset="100%" stopColor="hsl(0 84% 60%)" stopOpacity="0.1" />
            </radialGradient>
          </defs>

          {/* Grid rings */}
          {Array.from({ length: RING_COUNT }, (_, ringIndex) => {
            const radius = (MAX_RADIUS / RING_COUNT) * (ringIndex + 1);
            return (
              <polygon
                key={`ring-${ringIndex}`}
                points={getGridPolygonPoints(radius, sides)}
                fill="none"
                stroke="currentColor"
                strokeWidth="0.5"
                className="text-border/40"
              />
            );
          })}

          {/* Axis lines */}
          {Array.from({ length: sides }, (_, index) => {
            const end = polarToCartesian(CENTER_X, CENTER_Y, MAX_RADIUS, index * angleStep);
            return (
              <line
                key={`axis-${index}`}
                x1={CENTER_X}
                y1={CENTER_Y}
                x2={end.x}
                y2={end.y}
                stroke="currentColor"
                strokeWidth="0.5"
                className="text-border/30"
              />
            );
          })}

          {/* Data polygon */}
          {!isLoading && (
            <polygon
              points={getPolygonPoints(dimensions, MAX_RADIUS)}
              fill={`url(#${getAreaGradientId(averageScore)})`}
              stroke="hsl(var(--primary))"
              strokeWidth="2"
              strokeLinejoin="round"
              className="transition-all duration-700 ease-out"
            />
          )}

          {/* Loading skeleton polygon */}
          {isLoading && (
            <polygon
              points={getGridPolygonPoints(MAX_RADIUS * 0.5, sides)}
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeDasharray="8 4"
              className="text-muted-foreground/30 animate-pulse"
            />
          )}

          {/* Vertex dots */}
          {!isLoading &&
            dimensions.map((dimension, index) => {
              const radius = (Math.max(0, Math.min(100, dimension.value)) / 100) * MAX_RADIUS;
              const point = polarToCartesian(CENTER_X, CENTER_Y, radius, index * angleStep);
              return (
                <circle
                  key={`dot-${index}`}
                  cx={point.x}
                  cy={point.y}
                  r="4"
                  fill="hsl(var(--primary))"
                  stroke="hsl(var(--background))"
                  strokeWidth="2"
                  className="transition-all duration-700 ease-out"
                />
              );
            })}

          {/* Axis labels */}
          {dimensions.map((dimension, index) => {
            const labelPoint = polarToCartesian(
              CENTER_X,
              CENTER_Y,
              MAX_RADIUS + LABEL_OFFSET,
              index * angleStep,
            );
            return (
              <g key={`label-${index}`}>
                <text
                  x={labelPoint.x}
                  y={labelPoint.y - 6}
                  textAnchor="middle"
                  className="fill-current text-foreground"
                  fontSize="12"
                >
                  {dimension.icon}
                </text>
                <text
                  x={labelPoint.x}
                  y={labelPoint.y + 8}
                  textAnchor="middle"
                  className="fill-current text-muted-foreground"
                  fontSize="8"
                  fontWeight="500"
                >
                  {dimension.label}
                </text>
                {!isLoading && (
                  <text
                    x={labelPoint.x}
                    y={labelPoint.y + 18}
                    textAnchor="middle"
                    className="fill-current text-foreground"
                    fontSize="9"
                    fontWeight="700"
                  >
                    {Math.round(dimension.value)}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </CardContent>
    </Card>
  );
}
