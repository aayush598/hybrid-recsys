import type { Algorithm } from "../../types";

export interface AlgorithmOption {
  value: Algorithm;
  label: string;
  description?: string;
}

interface AlgorithmSelectorProps {
  value: Algorithm;
  onChange: (algorithm: Algorithm) => void;
  options?: AlgorithmOption[];
  disabled?: boolean;
  className?: string;
}

const DEFAULT_OPTIONS: AlgorithmOption[] = [
  { value: "hybrid", label: "Hybrid", description: "Blends every signal for the best picks" },
  { value: "collaborative", label: "Collaborative", description: "Loved by viewers like you" },
  { value: "content_based", label: "Content-Based", description: "Similar to what you rated highly" },
  { value: "trending", label: "Trending", description: "Popular across Orbo right now" },
  { value: "similar", label: "Similar Items", description: "More like your recent favorites" },
];

export default function AlgorithmSelector({
  value,
  onChange,
  options = DEFAULT_OPTIONS,
  disabled = false,
  className = "",
}: AlgorithmSelectorProps) {
  const selected = options.find((option) => option.value === value);

  return (
    <div className={`inline-flex flex-col gap-1 ${className}`}>
      <select
        value={value}
        disabled={disabled}
        aria-label="Recommendation algorithm"
        onChange={(event) => onChange(event.target.value as Algorithm)}
        className="bg-surface-800/80 border border-white/[0.08] rounded-lg text-sm font-medium text-zinc-200 px-3 py-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400/60 hover:border-white/[0.16] transition-colors"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value} className="bg-surface-900">
            {option.label}
          </option>
        ))}
      </select>
      {selected?.description && (
        <span className="text-2xs text-zinc-500">{selected.description}</span>
      )}
    </div>
  );
}
