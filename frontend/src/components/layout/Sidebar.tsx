"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FolderKanban,
  Download,
  Settings,
  ChevronLeft,
  ChevronRight,
  Factory,
  FileCode2,
  GitCompareArrows,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/templates", label: "Templates", icon: FileCode2 },
  { href: "/jobs/compare", label: "Compare", icon: GitCompareArrows },
  { href: "/exports", label: "Exports", icon: Download },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 flex h-screen flex-col glass-panel border-r border-[rgba(0,212,255,0.15)] transition-all duration-300",
        collapsed ? "w-16" : "w-56"
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-[rgba(0,212,255,0.1)] px-4">
        <Factory className="size-6 shrink-0 text-[#00d4ff]" />
        {!collapsed && (
          <span className="font-mono text-sm font-bold tracking-wider text-[#00d4ff] text-glow-cyan whitespace-nowrap">
            AI DATA FACTORY
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-2 py-4">
        {navItems.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-all duration-200 group",
                isActive
                  ? "border-l-2 border-[#00d4ff] bg-[rgba(0,212,255,0.1)] text-[#00d4ff] glow-cyan"
                  : "border-l-2 border-transparent text-[#6b7280] hover:bg-[rgba(255,255,255,0.05)] hover:text-[#e0e0e0]"
              )}
            >
              <item.icon
                className={cn(
                  "size-5 shrink-0 transition-colors",
                  isActive ? "text-[#00d4ff]" : "text-[#6b7280] group-hover:text-[#e0e0e0]"
                )}
              />
              {!collapsed && <span className="font-medium">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Collapse Toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex h-12 items-center justify-center border-t border-[rgba(0,212,255,0.1)] text-[#6b7280] transition-colors hover:text-[#00d4ff]"
      >
        {collapsed ? (
          <ChevronRight className="size-4" />
        ) : (
          <ChevronLeft className="size-4" />
        )}
      </button>
    </aside>
  );
}
