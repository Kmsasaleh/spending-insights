export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

// Must match the Category enum in backend/app/models.py.
export const CATEGORIES = [
  "Groceries", "Dining", "Transport", "Shopping", "Subscriptions",
  "Bills & Utilities", "Entertainment", "Health", "Travel",
  "Income", "Transfers", "Other",
] as const;
export type Category = (typeof CATEGORIES)[number];

export type Transaction = {
  posted_date: string;
  description: string;
  amount: string; // kept as text so cents stay exact; converted only for display
  merchant: string | null;
  category: Category | null;
  confidence: number | null;
  source: "memory" | "llm" | "user";
};

export type StoredTransaction = Transaction & { id: number };

export type CategorizeResponse = {
  transactions: Transaction[];
  parse_errors: string[];
  uncategorized: number;
  sent_to_claude: number;
  from_memory: number;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) {
    // FastAPI errors look like {"detail": "..."}
    const data = await res.json().catch(() => null);
    const detail = typeof data?.detail === "string" ? data.detail : `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return res.json();
}

export function uploadStatement(file: File) {
  const body = new FormData();
  body.append("file", file);
  return request<CategorizeResponse>("/categorize", { method: "POST", body });
}

export function getTransactions() {
  return request<StoredTransaction[]>("/transactions");
}

export function updateCategory(id: number, category: Category) {
  return request<StoredTransaction>(`/transactions/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category }),
  });
}