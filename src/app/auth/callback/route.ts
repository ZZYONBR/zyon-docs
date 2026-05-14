/**
 * Callback do Magic Link Supabase.
 * URL: /auth/callback?code=...&redirect=/docs/...
 *
 * Troca `code` por sessão (set cookies SSR) e redireciona para a página
 * que o usuário tentou acessar.
 */
import { NextRequest, NextResponse } from 'next/server';
import { createSupabaseServerClient } from '@/lib/auth/supabase-server';

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get('code');
  const redirect = searchParams.get('redirect') ?? '/docs';

  if (code) {
    const supabase = await createSupabaseServerClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}${redirect}`);
    }
    return NextResponse.redirect(
      `${origin}/login?reason=callback-failed`
    );
  }

  return NextResponse.redirect(`${origin}/login`);
}
