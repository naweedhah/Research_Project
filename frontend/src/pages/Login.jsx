import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot, Lock, Mail, User } from 'lucide-react';
import toast from 'react-hot-toast';
import { useApp } from '../context/AppContext';

function friendlyError(err) {
  if (err?.status === 401) return 'Invalid email or password.';
  if (err?.status === 409) return 'An account with this email already exists.';
  if (err?.status === 422) {
    return 'Please enter a valid email and a password of at least 8 characters.';
  }
  if (err instanceof TypeError) {
    return 'Cannot reach the server. Please check the backend connection.';
  }
  return err?.message || 'Something went wrong. Please try again.';
}

const inputClass =
  'w-full rounded-xl border border-slate-200 bg-surface py-3 pl-11 pr-3 text-base outline-none focus:border-secondary';
const labelClass = 'mb-1.5 block text-sm font-semibold text-slate-600';

export default function Login() {
  const [mode, setMode] = useState('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const { login, register } = useApp();
  const navigate = useNavigate();

  const isRegister = mode === 'register';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email.trim() || !password) {
      setError('Please enter both email and password.');
      return;
    }
    if (isRegister && name.trim().length < 2) {
      setError('Please enter your full name.');
      return;
    }
    if (isRegister && password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    setSubmitting(true);
    try {
      if (isRegister) {
        await register(name.trim(), email.trim(), password);
        toast.success('Account created');
      }
      await login(email.trim(), password);
      toast.success('Welcome to FedNutri-XAI');
      navigate('/research-home');
    } catch (err) {
      setError(friendlyError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-surface px-4">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,_rgba(108,92,231,0.18),_transparent_45%),radial-gradient(ellipse_at_bottom_right,_rgba(11,31,77,0.12),_transparent_40%)]" />
      <div className="relative w-full max-w-md animate-fade-in rounded-2xl border border-slate-100 bg-white p-8 shadow-xl">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-secondary text-white shadow-lg">
            <Bot size={28} />
          </div>
          <h1 className="text-2xl font-bold text-primary md:text-3xl">FedNutri-XAI</h1>
          <p className="mt-1 text-base text-slate-500">
            AI-Powered Childhood Nutrition Intelligence System
          </p>
          <p className="mt-3 text-base font-semibold text-secondary">
            {isRegister
              ? 'Create an account to access decision support'
              : 'Sign in to decision support'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {isRegister && (
            <div>
              <label className={labelClass} htmlFor="login-name">
                Full name
              </label>
              <div className="relative">
                <User size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  id="login-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoComplete="name"
                  className={inputClass}
                  placeholder="Your name"
                />
              </div>
            </div>
          )}

          <div>
            <label className={labelClass} htmlFor="login-email">
              Email
            </label>
            <div className="relative">
              <Mail size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                className={inputClass}
                placeholder="you@example.com"
              />
            </div>
          </div>

          <div>
            <label className={labelClass} htmlFor="login-password">
              Password
            </label>
            <div className="relative">
              <Lock size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                id="login-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={isRegister ? 'new-password' : 'current-password'}
                className={inputClass}
                placeholder={isRegister ? 'At least 8 characters' : 'Enter your password'}
              />
            </div>
          </div>

          {error && (
            <p className="rounded-xl bg-red-50 px-3 py-2.5 text-base text-danger" role="alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="mt-2 w-full rounded-full bg-gradient-to-r from-secondary to-[#4C6EF5] py-3 text-base font-bold text-white shadow-lg shadow-secondary/25 transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? 'Please wait...' : isRegister ? 'Create account' : 'Sign in'}
          </button>
        </form>

        <p className="mt-6 text-center text-base text-slate-600">
          {isRegister ? 'Already have an account?' : 'New to FedNutri-XAI?'}{' '}
          <button
            type="button"
            onClick={() => {
              setMode(isRegister ? 'login' : 'register');
              setError('');
            }}
            className="font-semibold text-secondary hover:underline"
          >
            {isRegister ? 'Sign in' : 'Create an account'}
          </button>
        </p>
      </div>
    </div>
  );
}
