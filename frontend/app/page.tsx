"use client";

import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import SignInForm from "@/components/SignInForm";
import SpendingApp from "@/components/SpendingApp";
import { supabase } from "@/lib/supabase";

export default function Home() {
  const [session, setSession] = useState<Session | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setChecking(false);
    });
    const { data } = supabase.auth.onAuthStateChange((_event, newSession) => setSession(newSession));
    return () => data.subscription.unsubscribe();
  }, []);

  if (checking) return null; // avoids a flash of the sign-in form for signed-in users
  if (!session) return <SignInForm />;

  // key: switching accounts gives a completely fresh app, so no data carries over.
  return <SpendingApp key={session.user.id} email={session.user.email ?? ""} />;
}