import Link from "next/link";
import { ReactNode } from "react";

import { TelegramSessionBootstrap } from "@/components/telegram-session-bootstrap";

const navItems = [
  { href: "/", label: "Сводка" },
  { href: "/dialogs", label: "Диалоги" },
  { href: "/clients", label: "Клиенты" },
  { href: "/bookings", label: "Записи" },
  { href: "/knowledge", label: "Знания" },
  { href: "/settings", label: "Настройки" },
];

export function AdminShell({ children }: { children: ReactNode }) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-kicker">BotReceptionist</span>
          <h1>Aster CRM</h1>
          <p>Операционная панель салона в Telegram.</p>
        </div>
        <nav className="nav">
          {navItems.map((item) => (
            <Link key={item.href} className="nav-link" href={item.href}>
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="content">
        <TelegramSessionBootstrap />
        {children}
      </main>
    </div>
  );
}
