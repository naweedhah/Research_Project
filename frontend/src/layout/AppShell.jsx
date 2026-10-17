import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { Bell, ChevronDown, LayoutGrid, LogOut, Menu, X } from 'lucide-react';
import { BRAND, COMPONENTS } from '../config/components';
import { NAV } from '../routes';
import { useApp } from '../context/AppContext';
import { apiRequest } from '../services/component4/httpClient';

function ApiStatus() {
  const [ok, setOk] = useState(null);
  useEffect(() => {
    const check = () => apiRequest('/health').then(() => setOk(true)).catch(() => setOk(false));
    check();
    const t = setInterval(check, 30000);
    return () => clearInterval(t);
  }, []);
  const label = ok == null ? 'Checking API…' : ok ? 'API connected' : 'API offline';
  return (
    <span className="hidden items-center gap-2 rounded-full border border-line bg-white px-3 py-1 text-xs font-medium text-muted sm:inline-flex">
      <span className={`h-2 w-2 rounded-full ${ok == null ? 'bg-slate-300' : ok ? 'bg-success' : 'bg-danger'}`} />
      {label}
    </span>
  );
}

function NavGroup({ component, items, onNavigate }) {
  const { pathname } = useLocation();
  const active = pathname.startsWith(component.path);
  const [open, setOpen] = useState(active);
  useEffect(() => {
    if (active) setOpen(true);
  }, [active]);
  const Icon = component.icon;
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-semibold transition ${
          active ? 'text-white' : 'text-white/70 hover:bg-white/5 hover:text-white'
        }`}
      >
        <span className={`flex h-6 w-6 items-center justify-center rounded-md ${component.bg}`}>
          <Icon size={14} className="text-white" />
        </span>
        <span className="flex-1">
          <span className="block text-[10px] font-medium uppercase tracking-wider text-white/40">C{component.number}</span>
          {component.title}
        </span>
        <ChevronDown size={15} className={`text-white/40 transition ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="ml-6 mt-1 space-y-0.5 border-l border-white/10 pl-3">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onNavigate}
              className={({ isActive }) =>
                `block rounded-md px-2.5 py-1.5 text-[13px] transition ${
                  isActive ? 'bg-white/10 font-semibold text-white' : 'text-white/60 hover:bg-white/5 hover:text-white'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}

function Sidebar({ open, onClose }) {
  return (
    <>
      {open && <button type="button" aria-label="Close menu" className="fixed inset-0 z-40 bg-black/40 lg:hidden" onClick={onClose} />}
      <aside
        className={`fixed left-0 top-0 z-50 flex h-screen w-[268px] flex-col bg-sidebar transition-transform duration-200 lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center gap-3 border-b border-white/10 px-5 py-4">
          <img src="/favicon.svg" alt="" className="h-9 w-9" />
          <div className="min-w-0">
            <p className="truncate text-sm font-bold text-white">{BRAND.short}</p>
            <p className="truncate text-[11px] text-white/50">{BRAND.tagline}</p>
          </div>
          <button type="button" className="ml-auto rounded p-1 text-white/60 hover:bg-white/10 lg:hidden" onClick={onClose} aria-label="Close menu">
            <X size={18} />
          </button>
        </div>
        <nav className="flex-1 space-y-2 overflow-y-auto px-3 py-4">
          <NavLink
            to="/"
            end
            onClick={onClose}
            className={({ isActive }) =>
              `mb-2 flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-semibold transition ${
                isActive ? 'bg-secondary text-white' : 'text-white/70 hover:bg-white/5 hover:text-white'
              }`
            }
          >
            <LayoutGrid size={17} /> Overview
          </NavLink>
          {COMPONENTS.map((c) => (
            <NavGroup key={c.id} component={c} items={NAV[c.id]} onNavigate={onClose} />
          ))}
        </nav>
        <p className="border-t border-white/10 px-5 py-3 text-[11px] leading-snug text-white/40">
          Research prototype · not for clinical use without professional review
        </p>
      </aside>
    </>
  );
}

export default function AppShell() {
  const [open, setOpen] = useState(false);
  const { profile, logout, warningCount } = useApp();
  return (
    <div className="min-h-screen">
      <Sidebar open={open} onClose={() => setOpen(false)} />
      <div className="lg:pl-[268px]">
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-line bg-white/90 px-4 py-2.5 backdrop-blur md:px-8">
          <button type="button" className="rounded-lg p-2 text-primary hover:bg-slate-100 lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
            <Menu size={20} />
          </button>
          <p className="hidden text-sm font-semibold text-primary md:block">{BRAND.name}</p>
          <div className="ml-auto flex items-center gap-3">
            <ApiStatus />
            <NavLink to="/c4/early-warning" className="relative rounded-lg p-2 text-muted hover:bg-slate-100" aria-label="District warnings">
              <Bell size={18} />
              {warningCount > 0 && (
                <span className="absolute -right-0.5 -top-0.5 rounded-full bg-danger px-1.5 text-[10px] font-bold text-white">{warningCount}</span>
              )}
            </NavLink>
            <div className="hidden text-right sm:block">
              <p className="text-sm font-semibold text-primary">{profile.name}</p>
              <p className="text-[11px] text-muted">{profile.role}</p>
            </div>
            <button type="button" onClick={logout} className="rounded-lg p-2 text-muted hover:bg-slate-100" aria-label="Sign out" title="Sign out">
              <LogOut size={18} />
            </button>
          </div>
        </header>
        <main className="mx-auto max-w-[1400px] px-4 py-6 md:px-8 md:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
