import { useState } from 'react';
import toast from 'react-hot-toast';
import { Loader2 } from 'lucide-react';
import { BRAND, COMPONENTS } from '../../config/components';
import { useApp } from '../../context/AppContext';

export default function Login() {
  const { login, register } = useApp();
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === 'register') {
        await register(form.name, form.email, form.password);
        toast.success('Account created');
      }
      await login(form.email, form.password);
    } catch (err) {
      toast.error(err.message || 'Sign-in failed');
    } finally {
      setBusy(false);
    }
  };

  const input = 'w-full rounded-lg border border-line bg-white px-3 py-2.5 text-sm outline-none transition focus:border-secondary focus:ring-2 focus:ring-secondary/20';

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <div className="hidden flex-col justify-between bg-sidebar p-12 text-white lg:flex">
        <div className="flex items-center gap-3">
          <img src="/favicon.svg" alt="" className="h-10 w-10" />
          <p className="text-lg font-bold">{BRAND.name}</p>
        </div>
        <div>
          <h1 className="max-w-lg text-4xl font-bold leading-tight">
            Early detection, interventions, model reliability and district planning in one place.
          </h1>
          <div className="mt-10 grid max-w-xl grid-cols-2 gap-3">
            {COMPONENTS.map((c) => (
              <div key={c.id} className="rounded-xl border border-white/10 bg-white/5 p-4">
                <span className={`mb-2 inline-flex h-7 w-7 items-center justify-center rounded-md ${c.bg}`}>
                  <c.icon size={15} />
                </span>
                <p className="text-sm font-semibold">C{c.number} · {c.title}</p>
                <p className="mt-1 text-xs text-white/60">{c.question}</p>
              </div>
            ))}
          </div>
        </div>
        <p className="text-xs text-white/40">{BRAND.tagline} · research prototype</p>
      </div>

      <div className="flex items-center justify-center p-6">
        <form onSubmit={submit} className="w-full max-w-sm space-y-4">
          <div>
            <h2 className="text-2xl font-bold text-primary">{mode === 'login' ? 'Sign in' : 'Create an account'}</h2>
            <p className="mt-1 text-sm text-muted">Use your project account to open the dashboard.</p>
          </div>
          {mode === 'register' && (
            <label className="block text-sm font-medium text-primary">
              Name
              <input className={`${input} mt-1`} value={form.name} onChange={set('name')} required autoComplete="name" />
            </label>
          )}
          <label className="block text-sm font-medium text-primary">
            Email
            <input className={`${input} mt-1`} type="email" value={form.email} onChange={set('email')} required autoComplete="email" />
          </label>
          <label className="block text-sm font-medium text-primary">
            Password
            <input className={`${input} mt-1`} type="password" value={form.password} onChange={set('password')} required minLength={6}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />
          </label>
          <button type="submit" disabled={busy}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-secondary py-2.5 text-sm font-semibold text-white transition hover:bg-secondary/90 disabled:opacity-60">
            {busy && <Loader2 size={16} className="animate-spin" />}
            {mode === 'login' ? 'Sign in' : 'Create account and sign in'}
          </button>
          <p className="text-center text-sm text-muted">
            {mode === 'login' ? 'No account yet?' : 'Already have an account?'}{' '}
            <button type="button" className="font-semibold text-secondary hover:underline" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
              {mode === 'login' ? 'Create one' : 'Sign in'}
            </button>
          </p>
        </form>
      </div>
    </div>
  );
}
