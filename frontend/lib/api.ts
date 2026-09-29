export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

// These mirror the Pydantic models in backend/app/main.py.
export type Category =
  | "Groceries" | "Dining" | "Transport" | "Shopping" | "Subscriptions"
  | "Bills & Utilities" | "Entertainment" | "Health" | "Travel"
  | "Income" | "Transfers" | "Other";

export type Transaction = {
  posted_date: string;
  description: string;
  amount: string; // kept as text so cents stay exact; converted only for display
  merchant: string | null;
  category: Category | null;
  confidence: number | null;
  source: "memory" | "llm";
};

export type CategorizeResponse = {
  transactions: Transaction[];
  parse_errors: string[];
  uncategorized: number;
  sent_to_claude: number;
  from_memory: number;
};

export async function uploadStatement(file: File): Promise<CategorizeResponse> {
  const body = new FormData();
  body.append("file", file);

  const res = await fetch(`${API_URL}/categorize`, { method: "POST", body });
  if (!res.ok) {
    // FastAPI errors look like {"detail": "Please upload a .csv file"}
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail ?? `Upload failed (${res.status})`);
  }
  return res.json();
}