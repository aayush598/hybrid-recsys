import { EyeOff } from "lucide-react";

interface ExcludeSeenToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  disabled?: boolean;
  className?: string;
}

export default function ExcludeSeenToggle({
  checked,
  onChange,
  label = "Exclude movies I've seen",
  disabled = false,
  className = "",
}: ExcludeSeenToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`group inline-flex items-center gap-2.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400/70 rounded-lg ${
        disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"
      } ${className}`}
    >
      <span
        aria-hidden="true"
        className={`relative inline-flex h-5 w-9 flex-shrink-0 items-center rounded-full border border-white/[0.08] transition-colors duration-200 ${
          checked ? "bg-brand-500" : "bg-surface-700 group-hover:bg-surface-600"
        }`}
      >
        <span
          className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform duration-200 ${
            checked ? "translate-x-4" : "translate-x-[3px]"
          }`}
        />
      </span>
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-400 group-hover:text-zinc-200 transition-colors">
        <EyeOff aria-hidden="true" className="w-3.5 h-3.5" />
        {label}
      </span>
    </button>
  );
}
