import type { ReactNode } from "react";
import { Info } from "lucide-react";

interface ExplanationTooltipProps {
  explanation: string;
  score?: number;
  children?: ReactNode;
  side?: "top" | "bottom";
  className?: string;
}

export default function ExplanationTooltip({
  explanation,
  score,
  children,
  side = "top",
  className = "",
}: ExplanationTooltipProps) {
  return (
    <span
      tabIndex={0}
      aria-label={`Why recommended: ${explanation}`}
      className={`relative inline-flex group focus:outline-none ${className}`}
    >
      {children ?? (
        <Info
          aria-hidden="true"
          className="w-3.5 h-3.5 text-zinc-500 group-hover:text-zinc-300 transition-colors"
        />
      )}
      <span
        role="tooltip"
        className={`pointer-events-none absolute left-1/2 -translate-x-1/2 z-20 w-56 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity duration-200 ${
          side === "top" ? "bottom-full mb-2" : "top-full mt-2"
        }`}
      >
        <span className="block rounded-md border border-white/10 bg-black/90 backdrop-blur-sm px-2.5 py-2 shadow-xl">
          {score !== undefined && (
            <span className="mb-1 block text-2xs font-semibold uppercase tracking-wider text-brand-400 tabular-nums">
              {(score * 100).toFixed(0)}% match
            </span>
          )}
          <span className="block text-2xs text-zinc-200 leading-relaxed">{explanation}</span>
        </span>
      </span>
    </span>
  );
}
