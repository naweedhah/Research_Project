"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";
import type { ClinicChildInput } from "@/data/clinic-board";

type ListResponse = {
  items: ClinicChildInput[];
  total: number;
  page: number;
  page_size: number;
};

/** Fetches every registered child through the existing paged /children endpoint. */
export async function fetchClinicChildren(): Promise<ClinicChildInput[]> {
  const first = await api<ListResponse>("/children?page=1&page_size=100");
  const items = [...first.items];
  const pages = Math.max(1, Math.ceil((first.total || items.length) / (first.page_size || 100)));
  for (let page = 2; page <= pages; page += 1) {
    const next = await api<ListResponse>(`/children?page=${page}&page_size=100`);
    items.push(...next.items);
  }
  return items;
}

export function useClinicChildren() {
  return useQuery({ queryKey: ["children", "clinic-board"], queryFn: fetchClinicChildren });
}
