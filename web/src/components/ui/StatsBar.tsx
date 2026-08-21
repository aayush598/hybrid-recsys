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
    { label: "Movies", value: health.movie_count.toLocaleString(), icon: "film" },
    { label: "Ratings", value: health.rating_count.toLocaleString(), icon: "star" },
    { label: "Users", value: health.user_count.toLocaleString(), icon: "users" },
    { label: "Status", value: health.status === "healthy" ? "Online" : "Degraded", icon: "check" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {stats.map((stat) => (
        <div key={stat.label} className="stat-card">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${stat.label === "Status" ? (stat.value === "Online" ? "bg-success" : "bg-warning") : "bg-accent/40"}`} />
            <span className="stat-label">{stat.label}</span>
          </div>
          <span className="stat-value text-xl">{stat.value}</span>
        </div>
      ))}
    </div>
  );
}
