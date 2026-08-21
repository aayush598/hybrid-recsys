"use client";

import { useState, useCallback, useRef } from "react";
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
  const [focused, setFocused] = useState(false);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

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
    <form onSubmit={handleSubmit} className="relative w-full group">
      <div
        className={`flex items-center gap-2 bg-white border rounded-xl transition-all duration-300 ${
          focused
            ? "border-neutral-400 ring-4 ring-black/5 shadow-sm"
            : "border-border hover:border-neutral-300 hover:shadow-sm"
        } ${size === "large" ? "px-5 py-3.5" : "px-4 py-2.5"}`}
      >
        <svg
          className={`text-muted shrink-0 transition-all duration-300 ${
            focused ? "text-primary" : ""
          } ${size === "large" ? "w-5 h-5" : "w-4 h-4"}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={placeholder}
          className={`flex-1 bg-transparent text-primary placeholder-muted focus:outline-none ${
            size === "large" ? "text-base" : "text-sm"
          }`}
        />
        {query && (
          <button
            type="button"
            onClick={() => {
              setQuery("");
              router.push("/movies");
              inputRef.current?.focus();
            }}
            className="text-muted hover:text-primary transition-colors duration-150"
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
