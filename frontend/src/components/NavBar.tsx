"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/",          label: "Dashboard"   },
  { href: "/master",    label: "Vendor Master" },
  { href: "/snapshots", label: "Snapshots"   },
  { href: "/jobs/new",  label: "New Job"     },
  { href: "/reports",   label: "Reports"     },
];

export default function NavBar() {
  const path = usePathname();
  return (
    <header className="bg-slate-900 text-white">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-6">
        <Link href="/" className="text-lg font-bold tracking-tight">Recon<span className="text-amber-400">·</span>AJWW</Link>
        <nav className="flex gap-1 ml-4">
          {TABS.map(t => {
            const active = (t.href === "/" ? path === "/" : path?.startsWith(t.href));
            return (
              <Link
                key={t.href}
                href={t.href}
                className={`px-3 py-1.5 rounded text-sm ${active ? "bg-white/15 text-white" : "text-slate-300 hover:bg-white/5 hover:text-white"}`}
              >
                {t.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
