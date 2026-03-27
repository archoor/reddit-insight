"use client";

import { cn } from "@/lib/utils";

interface ScoreRingProps {
  score: number;
  size?: "sm" | "md" | "lg";
  label?: string;
  className?: string;
}

const SIZE_CONFIG = {
  sm: { outer: 64, inner: 48, stroke: 6, fontSize: "text-lg font-bold", labelSize: "text-[9px]" },
  md: { outer: 88, inner: 68, stroke: 8, fontSize: "text-2xl font-bold", labelSize: "text-xs" },
  lg: { outer: 120, inner: 94, stroke: 10, fontSize: "text-3xl font-bold", labelSize: "text-sm" },
};

function getColor(score: number) {
  if (score >= 75) return "#16a34a";
  if (score >= 50) return "#ca8a04";
  return "#dc2626";
}

export function ScoreRing({ score, size = "md", label, className }: ScoreRingProps) {
  const { outer, stroke, fontSize, labelSize } = SIZE_CONFIG[size];
  const radius = (outer - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const color = getColor(score);

  return (
    <div className={cn("relative flex items-center justify-center", className)}>
      <svg width={outer} height={outer} className="-rotate-90">
        <circle
          cx={outer / 2}
          cy={outer / 2}
          r={radius}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={stroke}
        />
        <circle
          cx={outer / 2}
          cy={outer / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.5s ease" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center">
        <span className={cn(fontSize)} style={{ color }}>
          {score}
        </span>
        {label && (
          <span className={cn(labelSize, "text-muted-foreground")}>{label}</span>
        )}
      </div>
    </div>
  );
}
