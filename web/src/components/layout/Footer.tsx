import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-border bg-white mt-16">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="md:col-span-2">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-5 h-5 rounded bg-primary flex items-center justify-center">
                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                </svg>
              </div>
              <span className="text-sm font-semibold text-primary">RecSys</span>
            </div>
            <p className="text-sm text-secondary max-w-sm leading-relaxed">
              Hybrid recommendation engine combining collaborative filtering,
              content-based analysis, and ensemble methods. Built for Orbo.ai.
            </p>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-3">Product</h3>
            <ul className="space-y-2">
              <li><Link href="/movies" className="text-sm text-secondary hover:text-primary transition-colors">Explore</Link></li>
              <li><Link href="/trending" className="text-sm text-secondary hover:text-primary transition-colors">Trending</Link></li>
              <li><Link href="/about" className="text-sm text-secondary hover:text-primary transition-colors">About</Link></li>
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-3">Resources</h3>
            <ul className="space-y-2">
              <li><Link href="/docs" className="text-sm text-secondary hover:text-primary transition-colors">API Docs</Link></li>
              <li><a href="https://github.com/aayush598/hybrid-recsys" target="_blank" rel="noopener noreferrer" className="text-sm text-secondary hover:text-primary transition-colors">GitHub</a></li>
            </ul>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-xs text-muted">Built for Orbo.ai Assignment</p>
          <div className="flex items-center gap-3 text-xs text-muted">
            <span>Next.js 14</span>
            <span className="w-1 h-1 rounded-full bg-neutral-300" />
            <span>Neon PostgreSQL</span>
            <span className="w-1 h-1 rounded-full bg-neutral-300" />
            <span>Hybrid ML</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
