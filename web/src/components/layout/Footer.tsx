import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-surface-3 bg-surface-1 mt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="md:col-span-2">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="w-6 h-6 rounded-md bg-accent flex items-center justify-center">
                <svg
                  className="w-3.5 h-3.5 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
                  />
                </svg>
              </div>
              <span className="text-sm font-bold text-white">Hybrid RecSys</span>
            </div>
            <p className="text-sm text-slate-500 max-w-sm leading-relaxed">
              Production-grade hybrid recommendation system combining
              collaborative filtering, content-based analysis, and neural
              retrieval. Built for Orbo.ai&apos;s BeautyGPT use case.
            </p>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
              Product
            </h3>
            <ul className="space-y-2">
              <li>
                <Link
                  href="/movies"
                  className="text-sm text-slate-500 hover:text-white transition-colors"
                >
                  Explore Movies
                </Link>
              </li>
              <li>
                <Link
                  href="/trending"
                  className="text-sm text-slate-500 hover:text-white transition-colors"
                >
                  Trending
                </Link>
              </li>
              <li>
                <Link
                  href="/about"
                  className="text-sm text-slate-500 hover:text-white transition-colors"
                >
                  About
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
              Resources
            </h3>
            <ul className="space-y-2">
              <li>
                <Link
                  href="/docs"
                  className="text-sm text-slate-500 hover:text-white transition-colors"
                >
                  API Documentation
                </Link>
              </li>
              <li>
                <a
                  href="https://github.com/aayush598/hybrid-recsys"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-slate-500 hover:text-white transition-colors"
                >
                  GitHub
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-surface-3 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-xs text-slate-600">
            Built for Orbo.ai Assignment
          </p>
          <div className="flex items-center gap-4 text-xs text-slate-600">
            <span>Next.js 14</span>
            <span className="w-1 h-1 rounded-full bg-surface-4" />
            <span>Neon PostgreSQL</span>
            <span className="w-1 h-1 rounded-full bg-surface-4" />
            <span>Hybrid ML</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
