"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, persistCsrf } from "@/services/component4/httpClient";
import { Button } from "@/components/common/button";
import { Input, Label } from "@/components/common/field";
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
    <div className="flex min-h-screen items-center justify-center bg-[#eef2f7] p-6">
      <section className="w-full max-w-md">
        <form onSubmit={onSubmit} className="w-full rounded-2xl border border-line bg-white p-8 shadow-card">
          <div className="mb-8 text-center">
            <h2 className="text-[1.5rem] font-semibold tracking-[-0.025em] text-[#0A2748]">
              Sign in
            </h2>
            <p className="mt-1.5 text-[13px] font-normal leading-6 text-[#64748b]">
              Sign in with your account credentials.
            </p>
          </div>
          <div>
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" autoComplete="off" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="mt-4">
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" autoComplete="off" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <label className="mt-4 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
            Remember me on this workstation
          </label>
          {error ? <p className="mt-3 text-sm text-clinical-danger">{error}</p> : null}
          <Button className="mt-6 w-full" type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"} <ArrowRight className="h-4 w-4" />
          </Button>
        </form>
      </section>
    </div>
  );
}
