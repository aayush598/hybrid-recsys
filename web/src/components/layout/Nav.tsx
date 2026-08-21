"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";

const TEST_USERS = [
  { id: "user-1", label: "User 1 (71 ratings)" },
  { id: "user-10", label: "User 10" },
  { id: "user-50", label: "User 50" },
  { id: "user-100", label: "User 100" },
];

export default function Nav() {
  const pathname = usePathname();
  const [currentUser, setCurrentUser] = useState("user-1");
  const [showUserMenu, setShowUserMenu] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("hybrid-recsys-user");
    if (saved) setCurrentUser(saved);
  }, []);

  const switchUser = (userId: string) => {
    setCurrentUser(userId);
    localStorage.setItem("hybrid-recsys-user", userId);
    setShowUserMenu(false);
  };

  const navLinks = [
    { href: "/", label: "Home" },
    { href: "/movies", label: "Explore" },
    { href: "/trending", label: "Trending" },
    { href: "/about", label: "About" },
    { href: "/docs", label: "Docs" },
  ];

  return (
    <nav className="sticky top-0 z-50 bg-surface-0/80 backdrop-blur-xl border-b border-surface-3">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center">
                <svg
                  className="w-4 h-4 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z"
                  />
                </svg>
              </div>
              <span className="text-base font-bold text-white tracking-tight">
                Hybrid RecSys
              </span>
            </Link>

            <div className="hidden md:flex items-center gap-1">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={
                    pathname === link.href
                      ? "nav-link-active px-3 py-1.5"
                      : "nav-link px-3 py-1.5"
                  }
                >
                  {link.label}
                </Link>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-2 border border-surface-3 text-sm text-slate-300 hover:border-surface-4 hover:text-white transition-all"
              >
                <div className="w-5 h-5 rounded-full bg-accent/20 flex items-center justify-center">
                  <svg
                    className="w-3 h-3 text-accent"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
                  </svg>
                </div>
                <span className="hidden sm:inline">{currentUser}</span>
                <svg
                  className={`w-3.5 h-3.5 text-slate-500 transition-transform ${showUserMenu ? "rotate-180" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>

              {showUserMenu && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setShowUserMenu(false)}
                  />
                  <div className="absolute right-0 mt-2 w-56 bg-surface-2 border border-surface-3 rounded-xl shadow-2xl shadow-black/40 z-50 overflow-hidden">
                    <div className="px-3 py-2 border-b border-surface-3">
                      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                        Switch User
                      </p>
                    </div>
                    {TEST_USERS.map((user) => (
                      <button
                        key={user.id}
                        onClick={() => switchUser(user.id)}
                        className={`w-full text-left px-3 py-2.5 text-sm flex items-center gap-2 transition-colors ${
                          currentUser === user.id
                            ? "bg-accent/10 text-accent"
                            : "text-slate-300 hover:bg-surface-3"
                        }`}
                      >
                        <div
                          className={`w-2 h-2 rounded-full ${currentUser === user.id ? "bg-accent" : "bg-surface-4"}`}
                        />
                        {user.label}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>

            <Link
              href={`/profile/${currentUser}`}
              className="btn-ghost btn-sm hidden sm:inline-flex"
            >
              Profile
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}
