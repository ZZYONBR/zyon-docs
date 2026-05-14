/**
 * RBAC simples para docs.zzyon.com — decisão Rubens 10/05/2026.
 *
 * Nível 1 · Público (sem auth):  home, /docs/, /docs/inventario, /docs/quickstart,
 *                                /docs/decisoes/00X (ADRs públicos)
 * Nível 2 · Time Ícaro:           qualquer email @icaroexpress.com
 *
 * Conteúdo confidencial (Conselho, compensação, contratos sensíveis) NÃO
 * fica neste repo — fica em `icaro-conselho/` (git-crypt, repo separado).
 */
export const PUBLIC_PATHS = [
  '/',
  '/docs',
  '/docs/inventario',
  '/docs/quickstart',
  '/docs/decisoes/001-python-vs-typescript',
  '/docs/decisoes/002-multi-llm',
  '/docs/decisoes/003-mac-mini-prod',
  '/docs/decisoes/004-markdown-docs',
];

export const PUBLIC_PREFIXES = [
  '/login',
  '/auth/callback',
  '/logout',
  '/api/',
  '/og/',
  '/llms.txt',
  '/llms-full.txt',
  '/llms.mdx',
  '/_next/',
  '/favicon',
  '/icon',
];

export const ALLOWED_EMAIL_DOMAIN = '@icaroexpress.com';

export function isPublicRoute(pathname: string): boolean {
  if (PUBLIC_PATHS.includes(pathname)) return true;
  if (PUBLIC_PATHS.some((p) => pathname === p + '/')) return true;
  return PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

export function isAllowedEmail(email: string | null | undefined): boolean {
  if (!email) return false;
  return email.toLowerCase().endsWith(ALLOWED_EMAIL_DOMAIN);
}
