import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';
import type { CookieMethodsServer } from '@supabase/ssr';

/**
 * Cliente Supabase server-side (Server Components, Route Handlers, Server Actions).
 * Lê/grava cookies via next/headers para manter sessão.
 *
 * Uso:
 *   const supabase = await createSupabaseServerClient();
 *   const { data: { user } } = await supabase.auth.getUser();
 */
export async function createSupabaseServerClient() {
  const cookieStore = await cookies();
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
  if (!url || !key) {
    throw new Error('NEXT_PUBLIC_SUPABASE_URL/ANON_KEY não setados');
  }
  return createServerClient(url, key, {
    cookies: {
      getAll: () => cookieStore.getAll(),
      setAll: (toSet) => {
        try {
          toSet.forEach(({ name, value, options }) =>
            cookieStore.set({ name, value, ...options })
          );
        } catch {
          // Server Component: ignora; cookies só são setados em Route Handler / Server Action.
        }
      },
    } satisfies CookieMethodsServer,
  });
}
