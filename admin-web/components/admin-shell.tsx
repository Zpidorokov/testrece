"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { TelegramSessionBootstrap } from "@/components/telegram-session-bootstrap";

const navItems = [
  { href: "/", label: "Сводка", caption: "Операционный центр" },
  { href: "/dialogs", label: "Диалоги", caption: "Живые обращения" },
  { href: "/clients", label: "Клиенты", caption: "Карточки и статус" },
  { href: "/bookings", label: "Записи", caption: "Слоты и бронь" },
  { href: "/knowledge", label: "Знания", caption: "Факты для AI" },
  { href: "/settings", label: "Настройки", caption: "Каталоги и журнал" },
];

function isActive(pathname: string, href: string) {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AdminShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const activeItem = navItems.find((item) => isActive(pathname, item.href)) ?? navItems[0];

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-kicker">Telegram панель</span>
          <h1>Aster CRM</h1>
          <p>Компактная панель для диалогов, записи и базы знаний без лишнего шума.</p>
        </div>
        <nav className="nav desktop-nav">
          {navItems.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                aria-current={active ? "page" : undefined}
                className={`nav-link${active ? " nav-link-active" : ""}`}
                href={item.href}
              >
                <span>{item.label}</span>
                <small>{item.caption}</small>
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="workspace">
        <header className="mobile-header">
          <div className="mobile-header-copy">
            <span className="brand-kicker">Aster CRM</span>
            <strong>{activeItem.label}</strong>
            <small>{activeItem.caption}</small>
          </div>
          <span className="mobile-status">В работе</span>
        </header>

        <main className="content">
          <TelegramSessionBootstrap />
          <div className="content-frame">{children}</div>
        </main>

        <nav className="mobile-nav" aria-label="Основная навигация">
          {navItems.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                aria-current={active ? "page" : undefined}
                className={`mobile-nav-link${active ? " mobile-nav-link-active" : ""}`}
                href={item.href}
              >
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
