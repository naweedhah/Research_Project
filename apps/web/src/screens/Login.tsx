"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, persistCsrf } from "@/services/component4/httpClient";
import { Button } from "@/components/common/button";
import { Input, Label } from "@/components/common/field";
import { LoginAtmosphere } from "@/components/futuristic/login-atmosphere";
import { ArrowRight } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const session = await api<{ csrf_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password, remember_me: remember }),
      });
      persistCsrf(session.csrf_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-screen bg-[#0E243D] lg:grid-cols-[1.35fr_0.85fr]">
      <section className="relative hidden overflow-hidden lg:block" aria-hidden>
        <LoginAtmosphere />
      </section>
      <section className="flex items-center justify-center bg-[#EEF3F6] p-6">
        <form onSubmit={onSubmit} className="w-full max-w-md rounded-[28px] border border-white/80 bg-white/85 p-8 shadow-card backdrop-blur-xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#3E75B8]">Paediatric nutrition intelligence</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[#102A4C]">Sign in</h1>
          <p className="mt-1 text-sm leading-6 text-[#5C6E82]">Current WHO assessment and 12-month nutritional risk for every child you follow.</p>
          <div className="mt-8">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="mt-4">
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <label className="mt-4 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
            Remember me on this workstation
          </label>
          {error ? (
            <p className="mt-3 text-sm text-clinical-danger" role="alert">
              {error}
            </p>
          ) : null}
          <Button className="mt-6 w-full" type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"} <ArrowRight className="h-4 w-4" />
          </Button>
          <details className="mt-6 text-xs text-[#5C6E82]">
            <summary className="cursor-pointer font-medium">Demonstration access</summary>
            <p className="mt-2">Use the clinic demonstration account already configured for this workstation.</p>
          </details>
          <p className="mt-6 text-[11px] text-[#5C6E82]">Research decision-support prototype. Clinician confirmation required.</p>
        </form>
      </section>
    </div>
  );
}
