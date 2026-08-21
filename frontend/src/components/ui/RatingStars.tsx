import { useState } from "react";
import { Star } from "lucide-react";

interface RatingStarsProps {
  value: number;
  onChange?: (value: number) => void;
  readOnly?: boolean;
  size?: "sm" | "md" | "lg";
  maxStars?: number;
  className?: string;
}

const SIZE_CLASSES: Record<NonNullable<RatingStarsProps["size"]>, string> = {
  sm: "w-3.5 h-3.5",
  md: "w-5 h-5",
  lg: "w-7 h-7",
};

export default function RatingStars({
  value,
  onChange,
  readOnly = false,
  size = "md",
  maxStars = 5,
  className = "",
}: RatingStarsProps) {
  const [hovered, setHovered] = useState<number | null>(null);
  const interactive = !readOnly && typeof onChange === "function";
  const displayValue = hovered ?? value;

  return (
    <div
      className={`inline-flex items-center gap-0.5 ${className}`}
      role={interactive ? "radiogroup" : "img"}
      aria-label={`Rating: ${value} out of ${maxStars} stars`}
      onMouseLeave={() => setHovered(null)}
    >
      {Array.from({ length: maxStars }, (_, index) => {
        const starValue = index + 1;
        const filled = starValue <= Math.round(displayValue);
        const icon = (
          <Star
            aria-hidden="true"
            className={`${SIZE_CLASSES[size]} transition-colors duration-150 ${
              filled ? "text-amber-400 fill-amber-400" : "text-zinc-600"
            }`}
          />
        );

        if (!interactive) {
          return <span key={starValue}>{icon}</span>;
        }

        return (
          <button
            key={starValue}
            type="button"
            role="radio"
            aria-checked={value === starValue}
            aria-label={`Rate ${starValue} star${starValue > 1 ? "s" : ""}`}
            className="rounded p-0 bg-transparent border-none focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400/70"
            onClick={() => onChange?.(starValue)}
            onMouseEnter={() => setHovered(starValue)}
          >
            {icon}
          </button>
        );
      })}
    </div>
  );
}
