"use client";

import { useState } from "react";

export default function RatingWidget({
  movieId,
  userId,
  onRated,
}: {
  movieId: number;
  userId: string;
  onRated?: (rating: number) => void;
}) {
  const [rating, setRating] = useState(0);
  const [hovered, setHovered] = useState(0);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const submitRating = async (value: number) => {
    if (submitting) return;
    setSubmitting(true);
    try {
      const res = await fetch(
        `/api/recommendations/user/${userId}/rate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ movie_id: movieId, rating: value }),
        }
      );
      if (res.ok) {
        setRating(value);
        setSubmitted(true);
        onRated?.(value);
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="flex items-center gap-2 text-success">
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="text-sm font-medium">Rated {rating.toFixed(1)}</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            disabled={submitting}
            onMouseEnter={() => setHovered(star)}
            onMouseLeave={() => setHovered(0)}
            onClick={() => submitRating(star)}
            className="p-0.5 transition-transform hover:scale-110 disabled:opacity-50"
          >
            <svg
              className={`w-6 h-6 transition-colors ${
                star <= (hovered || rating)
                  ? "text-warning"
                  : "text-surface-4 hover:text-surface-3"
              }`}
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
          </button>
        ))}
      </div>
      <span className="text-xs text-slate-500">
        {hovered > 0 ? `${hovered}/5` : "Rate this"}
      </span>
    </div>
  );
}
