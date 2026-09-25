import type { ConversationDetail, ConversationSummary } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const API_TOKEN = import.meta.env.VITE_API_TOKEN;

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: API_TOKEN ? { Authorization: `Bearer ${API_TOKEN}` } : undefined,
    });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export function listConversations(): Promise<ConversationSummary[] | null> {
  return fetchJson<ConversationSummary[]>("/api/conversations");
}

export function getConversation(id: string): Promise<ConversationDetail | null> {
  return fetchJson<ConversationDetail>(`/api/conversations/${id}`);
}
