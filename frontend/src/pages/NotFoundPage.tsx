import { Link } from "react-router-dom";
import { Home, Search, Film } from "lucide-react";

export default function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="surface-card p-12 text-center max-w-md">
        <div className="text-6xl font-bold text-zinc-800 mb-4">404</div>
        <div className="w-14 h-14 rounded-2xl bg-surface-750 flex items-center justify-center mx-auto mb-4">
          <Film className="w-6 h-6 text-zinc-600" />
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">
          Page not found
        </h2>
        <p className="text-sm text-zinc-500 mb-6">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link
            to="/"
            className="btn-primary px-4 py-2 text-sm inline-flex items-center gap-2"
          >
            <Home className="w-4 h-4" />
            Home
          </Link>
          <Link
            to="/explore"
            className="btn-secondary px-4 py-2 text-sm inline-flex items-center gap-2"
          >
            <Search className="w-4 h-4" />
            Explore
          </Link>
        </div>
      </div>
    </div>
  );
}
