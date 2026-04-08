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
      <header className="mobile-header">
        <div>
          <span className="brand-kicker">Aster CRM</span>
          <strong>Управление салоном</strong>
        </div>
        <span className="badge">Telegram</span>
      </header>

      <aside className="sidebar">
        <div className="brand">
          <span className="brand-kicker">BotReceptionist</span>
          <h1>Aster CRM</h1>
          <p>Операционная панель салона в Telegram без лишнего шума.</p>
        </div>
        <nav className="nav desktop-nav">
          {navItems.map((item) => (
            <Link key={item.href} className="nav-link" href={item.href}>
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="content">
        <TelegramSessionBootstrap />
        <div className="content-frame">{children}</div>
      </main>
      <nav className="mobile-nav">
        {navItems.map((item) => (
          <Link key={item.href} className="mobile-nav-link" href={item.href}>
            {item.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
