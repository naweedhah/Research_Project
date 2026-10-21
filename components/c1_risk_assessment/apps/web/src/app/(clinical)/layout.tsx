import { AppShell } from "@/components/layout/app-shell";

export default function ClinicalLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
