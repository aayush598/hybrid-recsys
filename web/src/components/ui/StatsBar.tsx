"use client";

import { useState, useEffect } from "react";

interface HealthData {
  status: string;
  movie_count: number;
  rating_count: number;
  user_count: number;
}

export default function StatsBar() {
  const [health, setHealth] = useState<HealthData | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => {});
  }, []);

  if (!health) return null;

  const stats = [
    { label: "Movies", value: health.movie_count.toLocaleString() },
    { label: "Ratings", value: health.rating_count.toLocaleString() },
    { label: "Users", value: health.user_count.toLocaleString() },
    { label: "Status", value: health.status === "healthy" ? "Online" : "Degraded", isStatus: true },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {stats.map((stat) => (
        <div key={stat.label} className="stat-card">
          <span className="stat-label">{stat.label}</span>
          <span className="stat-value text-xl">
            {stat.isStatus && (
              <span className={`inline-block w-2 h-2 rounded-full mr-2 ${stat.value === "Online" ? "bg-green-500" : "bg-amber-500"}`} />
            )}
            {stat.value}
          </span>
        </div>
      ))}
    </div>
  );
}
