/**
 * docs.zzyon.com · Middleware
 *
 * 1) Auth gate (Supabase SSR cookies)
 *    - Rotas públicas: passa direto (home, /docs, /docs/inventario, ADRs públicos, assets)
 *    - Outras /docs/*: exige sessão + email @icaroexpress.com
 *
 * 2) Preserva o proxy original do Fumadocs (negotiation markdown + rewrites
 *    .mdx → /llms.mdx/docs/.../content.md). Importado e chamado se nenhuma
 *    auth redirect aconteceu.
 */
import { NextRequest, NextResponse } from 'next/server';
import { createServerClient } from '@supabase/ssr';
import { isMarkdownPreferred, rewritePath } from 'fumadocs-core/negotiation';
import { docsContentRoute, docsRoute } from '@/lib/shared';
import { isPublicRoute, isAllowedEmail, ALLOWED_EMAIL_DOMAIN } from '@/lib/auth/rbac';

const { rewrite: rewriteDocs } = rewritePath(
  `${docsRoute}{/*path}`,
  `${docsContentRoute}{/*path}/content.md`,
);
const { rewrite: rewriteSuffix } = rewritePath(
  `${docsRoute}{/*path}.mdx`,
  `${docsContentRoute}{/*path}/content.md`,
);

async function checkAuth(request: NextRequest): Promise<NextResponse | null> {
  const { pathname } = request.nextUrl;
  if (isPublicRoute(pathname)) return null;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) {
    // Sem config: por segurança, libera (dev) — em prod, sempre seta env
    console.warn('[middleware] Supabase env não setado, liberando rota privada');
    return null;
  }

  // Resposta inicial para o Supabase SSR usar pra atualizar cookies
  let response = NextResponse.next({ request });
  const supabase = createServerClient(url, key, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (toSet) => {
        toSet.forEach(({ name, value, options }) =>
          response.cookies.set({ name, value, ...options })
        );
      },
    },
  });

  const { data: { user } } = await supabase.auth.getUser();
  if (!user || !isAllowedEmail(user.email)) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    if (user && !isAllowedEmail(user.email)) {
      loginUrl.searchParams.set('reason', 'wrong-domain');
    }
    return NextResponse.redirect(loginUrl);
  }
  return response;
}

export async function middleware(request: NextRequest) {
  // 1) Auth gate
  const authResp = await checkAuth(request);
  if (authResp) {
    // Aplica rewrites do proxy também (auth liberou a navegação)
    const url = request.nextUrl.pathname;
    const r1 = rewriteSuffix(url);
    if (r1) return NextResponse.rewrite(new URL(r1, request.nextUrl));
    if (isMarkdownPreferred(request)) {
      const r2 = rewriteDocs(url);
      if (r2) return NextResponse.rewrite(new URL(r2, request.nextUrl));
    }
    return authResp;
  }

  // 2) Sem auth gate disparado — repassa rewrites do proxy original
  const url = request.nextUrl.pathname;
  const r1 = rewriteSuffix(url);
  if (r1) return NextResponse.rewrite(new URL(r1, request.nextUrl));
  if (isMarkdownPreferred(request)) {
    const r2 = rewriteDocs(url);
    if (r2) return NextResponse.rewrite(new URL(r2, request.nextUrl));
  }
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Roda em todas as rotas exceto:
     * - /_next/static (estáticos do build)
     * - /_next/image (otimização de imagem)
     * - /favicon.ico / icon files
     */
    '/((?!_next/static|_next/image|favicon.ico|icon).*)',
  ],
};
