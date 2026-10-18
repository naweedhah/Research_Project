import { redirect } from "next/navigation";

export default function RegisterChildRedirectPage() {
  redirect("/children?register=1");
}
