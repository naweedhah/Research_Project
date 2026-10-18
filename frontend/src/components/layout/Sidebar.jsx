import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  LineChart,
  Map,
  Package,
  BellRing,
  TrendingUp,
  Brain,
  MapPinned,
  Settings,
  Bot,
  Sparkles,
  X,
  Home,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

const menu = [
  { to: '/research-home', label: 'Research Hub', icon: Home },
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/forecast', label: 'Forecast', icon: LineChart },
  { to: '/gis-map', label: 'GIS Risk Map', icon: Map },
  { to: '/resource-planning', label: 'Resource Planning', icon: Package },
  { to: '/early-warning', label: 'Early Warning', icon: BellRing },
  { to: '/trend-analysis', label: 'Trend Analysis', icon: TrendingUp },
  { to: '/explainable-ai', label: 'Explainable AI', icon: Brain },
  { to: '/district-details', label: 'District Details', icon: MapPinned },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar({ open = false, onClose }) {
  const { setAssistantOpen } = useApp();

  return (
    <>
      {open && (
        <button
          type="button"
          aria-label="Close menu overlay"
          className="fixed inset-0 z-40 bg-primary/40 md:hidden"
          onClick={onClose}
        />
      )}
      <aside
        className={`fixed left-0 top-0 z-50 flex h-screen w-[260px] flex-col bg-primary text-white shadow-xl transition-transform duration-300 md:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
      <div className="border-b border-white/10 px-5 py-5">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-secondary/90 shadow-lg shadow-secondary/30">
              <Bot className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-lg font-bold leading-tight">FedNutri-XAI</h1>
              <p className="text-sm leading-snug text-white/60">
                AI Child Nutrition Intelligence
              </p>
            </div>
          </div>
          <button type="button" className="rounded-lg p-1.5 hover:bg-white/10 md:hidden" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {menu.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onClose}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-2.5 text-base transition ${
                isActive
                  ? 'bg-secondary text-white shadow-md shadow-secondary/25'
                  : 'text-white/75 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            <Icon className="h-4.5 w-4.5 shrink-0" size={19} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-white/10 p-4">
        <div className="rounded-2xl bg-gradient-to-br from-secondary/40 to-white/5 p-4">
          <div className="mb-3 flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-secondary">
              <Bot size={18} />
            </div>
            <div>
              <p className="text-base font-semibold">AI Health Assistant</p>
              <p className="text-sm text-white/60">Ask AI about nutrition data</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              setAssistantOpen(true);
              onClose?.();
            }}
            className="flex w-full items-center justify-center gap-2 rounded-full bg-white px-3 py-2 text-base font-semibold text-primary transition hover:bg-white/90"
          >
            <Sparkles size={14} className="text-secondary" />
            Open Assistant
          </button>
        </div>
      </div>
    </aside>
    </>
  );
}
