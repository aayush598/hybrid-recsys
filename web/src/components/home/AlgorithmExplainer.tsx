export default function AlgorithmExplainer() {
  const stages = [
    {
      step: "01",
      title: "Candidate Generation",
      description: "ALS collaborative filtering retrieves top candidates from 9,786 movies using latent factor dot products.",
      tag: "Collaborative Filtering",
    },
    {
      step: "02",
      title: "Content Similarity",
      description: "TF-IDF features + genre vectors compute cosine similarity for content-based candidates.",
      tag: "Content-Based",
    },
    {
      step: "03",
      title: "Hybrid Ensemble",
      description: "Late fusion combines CF (60%) + trending boost (5%) with diversity-aware re-ranking.",
      tag: "Hybrid",
    },
  ];

  return (
    <div className="card p-6">
      <div className="flex items-center gap-2 mb-5">
        <svg className="w-4 h-4 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
        </svg>
        <h2 className="section-title">How It Works</h2>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {stages.map((stage) => (
          <div key={stage.step} className="flex gap-3">
            <div className="shrink-0 w-8 h-8 rounded-lg bg-neutral-100 flex items-center justify-center">
              <span className="text-xs font-bold text-secondary">{stage.step}</span>
            </div>
            <div className="space-y-1.5">
              <h3 className="text-sm font-semibold text-primary">{stage.title}</h3>
              <p className="text-xs text-secondary leading-relaxed">{stage.description}</p>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-2xs font-medium bg-neutral-100 text-secondary border border-border">
                {stage.tag}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
