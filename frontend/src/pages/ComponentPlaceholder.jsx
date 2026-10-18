import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Bot, Construction, LogOut } from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function ComponentPlaceholder({
  componentNumber,
  title,
  description,
}) {
  const { logout } = useApp();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-surface">
      <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3 md:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-secondary text-white">
              <Bot size={20} />
            </div>
            <div>
              <p className="text-sm font-bold text-primary">FedNutri-XAI</p>
              <p className="text-[11px] text-slate-500">Component 0{componentNumber}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              logout();
              navigate('/login');
            }}
            className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 px-3 py-2 text-xs font-semibold text-primary hover:bg-slate-50"
          >
            <LogOut size={14} /> Logout
          </button>
        </div>
      </header>

      <main className="mx-auto flex max-w-3xl flex-col items-center px-4 py-16 text-center md:py-24">
        <div className="w-full animate-fade-in rounded-2xl border border-slate-100 bg-white p-8 shadow-sm md:p-12">
          <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-secondary/10 text-secondary">
            <Construction size={28} />
          </div>
          <span className="mb-3 inline-block rounded-full bg-slate-100 px-3 py-1 text-[10px] font-bold tracking-wide text-slate-500">
            COMING SOON
          </span>
          <h1 className="text-2xl font-bold text-primary md:text-3xl">Component Under Development</h1>
          <p className="mt-2 text-sm font-semibold text-secondary">{title}</p>
          <p className="mx-auto mt-4 max-w-lg text-sm leading-relaxed text-slate-500">
            {description}
          </p>
          <p className="mx-auto mt-3 max-w-lg text-sm leading-relaxed text-slate-400">
            Detailed capabilities for this research component will be integrated here in a future
            iteration of the FedNutri-XAI platform.
          </p>
          <Link
            to="/research-home"
            className="mt-8 inline-flex items-center gap-2 rounded-full bg-secondary px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-secondary/25"
          >
            <ArrowLeft size={16} /> Back to Research Hub
          </Link>
        </div>
      </main>
    </div>
  );
}
