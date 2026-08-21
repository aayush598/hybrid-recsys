"use client";

import { useEffect, useRef, useState } from "react";

const stages = [
  {
    step: "01",
    title: "Candidate Generation",
    description: "ALS collaborative filtering retrieves top candidates from 9,786 movies using latent factor dot products.",
    tag: "Collaborative Filtering",
    icon: "M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z",
  },
  {
    step: "02",
    title: "Content Similarity",
    description: "TF-IDF features + genre vectors compute cosine similarity for content-based candidates.",
    tag: "Content-Based",
    icon: "M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z",
  },
  {
    step: "03",
    title: "Hybrid Ensemble",
    description: "Late fusion combines CF (60%) + trending boost (5%) with diversity-aware re-ranking.",
    tag: "Hybrid",
    icon: "M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5",
  },
];

export default function AlgorithmExplainer() {
  const [visible, setVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); obs.disconnect(); } },
      { threshold: 0.2 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <div ref={ref} className="card p-6 h-full">
      <div className="flex items-center gap-2 mb-5">
        <svg className="w-4 h-4 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
        </svg>
        <h2 className="section-title">How It Works</h2>
      </div>
      <div className="space-y-4">
        {stages.map((stage, i) => (
          <div
            key={stage.step}
            className="flex gap-3 p-3 rounded-lg hover:bg-neutral-50 transition-all duration-300 group cursor-default"
            style={{ opacity: visible ? 1 : 0, transform: visible ? "translateX(0)" : "translateX(-12px)", transition: `all 0.5s cubic-bezier(0.16,1,0.3,1) ${i * 120}ms` }}
          >
            <div className="shrink-0 w-9 h-9 rounded-lg bg-neutral-100 flex items-center justify-center group-hover:bg-primary group-hover:text-white transition-colors duration-300">
              <svg className="w-4 h-4 text-secondary group-hover:text-white transition-colors duration-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d={stage.icon} />
              </svg>
            </div>
            <div className="space-y-1.5 flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-primary">{stage.title}</h3>
                <span className="text-2xs font-mono text-muted">{stage.step}</span>
              </div>
              <p className="text-xs text-secondary leading-relaxed">{stage.description}</p>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-2xs font-medium bg-neutral-100 text-secondary border border-border group-hover:border-neutral-300 transition-colors">
                {stage.tag}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
