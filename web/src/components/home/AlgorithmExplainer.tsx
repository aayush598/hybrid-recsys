export default function AlgorithmExplainer() {
  const stages = [
    {
      step: "01",
      title: "Candidate Generation",
      description:
        "ALS collaborative filtering retrieves top candidates from 9,786 movies using latent factor dot products.",
      tag: "Collaborative Filtering",
      color: "accent",
    },
    {
      step: "02",
      title: "Content Similarity",
      description:
        "TF-IDF features + genre vectors compute cosine similarity for content-based candidates.",
      tag: "Content-Based",
      color: "success",
    },
    {
      step: "03",
      title: "Hybrid Ensemble",
      description:
        "Late fusion combines CF (60%) + trending boost (5%) with diversity-aware re-ranking.",
      tag: "Hybrid",
      color: "warning",
    },
  ];

  const colorMap: Record<string, string> = {
    accent: "bg-accent/10 text-accent border-accent/20",
    success: "bg-success/10 text-success border-success/20",
    warning: "bg-warning/10 text-warning border-warning/20",
  };

  return (
    <div className="card p-6">
      <div className="flex items-center gap-2 mb-5">
        <svg className="w-4 h-4 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
        </svg>
        <h2 className="section-title">How It Works</h2>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {stages.map((stage) => (
          <div key={stage.step} className="flex gap-3">
            <div className="shrink-0 w-8 h-8 rounded-lg bg-surface-3 flex items-center justify-center">
              <span className="text-xs font-bold text-slate-400">{stage.step}</span>
            </div>
            <div className="space-y-1.5">
              <h3 className="text-sm font-semibold text-white">{stage.title}</h3>
              <p className="text-xs text-slate-500 leading-relaxed">{stage.description}</p>
              <span className={`inline-flex items-center px-2 py-0.5 rounded text-2xs font-medium border ${colorMap[stage.color]}`}>
                {stage.tag}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
