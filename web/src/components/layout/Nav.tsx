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
    <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-border">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-primary flex items-center justify-center">
                <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                </svg>
              </div>
              <span className="text-sm font-semibold text-primary">RecSys</span>
            </Link>

            <div className="hidden md:flex items-center gap-1">
              {navLinks.map((link) => {
                const isActive = pathname === link.href;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                      isActive
                        ? "text-primary bg-neutral-100"
                        : "text-secondary hover:text-primary hover:bg-neutral-50"
                    }`}
                  >
                    {link.label}
                  </Link>
                );
              })}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border text-sm text-secondary hover:border-neutral-300 hover:text-primary transition-all bg-white"
              >
                <div className="w-5 h-5 rounded-full bg-neutral-200 flex items-center justify-center">
                  <svg className="w-3 h-3 text-secondary" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
                  </svg>
                </div>
                <span className="hidden sm:inline">{currentUser}</span>
                <svg className={`w-3.5 h-3.5 text-muted transition-transform ${showUserMenu ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {showUserMenu && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setShowUserMenu(false)} />
                  <div className="absolute right-0 mt-2 w-56 bg-white border border-border rounded-xl shadow-lg z-50 overflow-hidden">
                    <div className="px-3 py-2 border-b border-border">
                      <p className="text-xs font-medium text-muted uppercase tracking-wider">Switch User</p>
                    </div>
                    {TEST_USERS.map((user) => (
                      <button
                        key={user.id}
                        onClick={() => switchUser(user.id)}
                        className={`w-full text-left px-3 py-2.5 text-sm flex items-center gap-2 transition-colors ${
                          currentUser === user.id
                            ? "bg-neutral-100 text-primary font-medium"
                            : "text-secondary hover:bg-neutral-50"
                        }`}
                      >
                        <div className={`w-2 h-2 rounded-full ${currentUser === user.id ? "bg-primary" : "bg-neutral-300"}`} />
                        {user.label}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>

            <Link href={`/profile/${currentUser}`} className="btn-ghost btn-sm hidden sm:inline-flex">
              Profile
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}
