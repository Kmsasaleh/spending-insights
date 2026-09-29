import { createClient } from "@supabase/supabase-js";

// Uses the PUBLISHABLE key, which is safe in the browser.
// The secret key lives only on the backend.
export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!
);