import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BeautyRec - AI Movie Recommendations",
  description: "Hybrid recommendation system powered by collaborative filtering and content-based analysis",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 min-h-screen">
        <nav className="bg-gray-900 border-b border-gray-800 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <a href="/" className="flex items-center gap-2">
                <span className="text-2xl">🎬</span>
                <span className="text-xl font-bold bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">
                  BeautyRec
                </span>
              </a>
              <div className="flex items-center gap-6">
                <a href="/" className="text-gray-300 hover:text-white transition">Home</a>
                <a href="/movies" className="text-gray-300 hover:text-white transition">Explore</a>
                <a href="/trending" className="text-gray-300 hover:text-white transition">Trending</a>
                <a href="/profile/user-1" className="text-gray-300 hover:text-white transition">Profile</a>
              </div>
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">{children}</main>
      </body>
    </html>
  );
}
