"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";

export default function SearchBar({
  placeholder = "Search movies...",
  defaultValue = "",
  size = "default",
}: {
  placeholder?: string;
  defaultValue?: string;
  size?: "default" | "large";
}) {
  const [query, setQuery] = useState(defaultValue);
  const router = useRouter();

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (query.trim()) {
        router.push(`/movies?q=${encodeURIComponent(query.trim())}`);
      } else {
        router.push("/movies");
      }
    },
    [query, router]
  );

  return (
    <form onSubmit={handleSubmit} className="relative w-full">
      <div
        className={`flex items-center gap-2 bg-surface-2 border border-surface-3 rounded-xl focus-within:border-accent focus-within:ring-1 focus-within:ring-accent/30 transition-all ${size === "large" ? "px-5 py-3.5" : "px-4 py-2.5"}`}
      >
        <svg
          className={`text-slate-500 shrink-0 ${size === "large" ? "w-5 h-5" : "w-4 h-4"}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
          />
        </svg>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          className={`flex-1 bg-transparent text-white placeholder-slate-500 focus:outline-none ${size === "large" ? "text-base" : "text-sm"}`}
        />
        {query && (
          <button
            type="button"
            onClick={() => {
              setQuery("");
              router.push("/movies");
            }}
            className="text-slate-500 hover:text-white transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
    </form>
  );
}
