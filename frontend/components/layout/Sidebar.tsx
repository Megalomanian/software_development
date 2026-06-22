"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Database,
  FlaskConical,
  BarChart3,
  Rocket,
  Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { label: "概览", href: "/", icon: LayoutDashboard },
  { label: "数据", href: "/data", icon: Database },
  { label: "实验", href: "/experiments", icon: FlaskConical },
  { label: "模型", href: "/models", icon: BarChart3 },
  { label: "部署", href: "/deployments", icon: Rocket },
  { label: "监控", href: "/monitoring", icon: Activity },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 bg-white border-r flex flex-col p-4 shrink-0">
      <div className="text-xl font-bold mb-8 px-2">ML Platform</div>
      <nav className="flex flex-col gap-1">
        {navItems.map(({ label, href, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
              pathname === href
                ? "bg-blue-50 text-blue-700 font-medium"
                : "text-gray-600 hover:bg-gray-100"
            )}
          >
            <Icon className="w-4 h-4" />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
