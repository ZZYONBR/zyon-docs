'use client';
import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { getSupabaseBrowser } from '@/lib/auth/supabase-browser';
import { ALLOWED_EMAIL_DOMAIN } from '@/lib/auth/rbac';

function LoginContent() {
  const search = useSearchParams();
  const router = useRouter();
  const redirect = search.get('redirect') ?? '/docs';
  const reason = search.get('reason');
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const [msg, setMsg] = useState('');

  // Se já autenticado, manda direto pra /docs
  useEffect(() => {
    (async () => {
      const sb = getSupabaseBrowser();
      const { data: { user } } = await sb.auth.getUser();
      if (user) router.replace(redirect);
    })();
  }, [redirect, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus('sending');
    setMsg('');
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail.endsWith(ALLOWED_EMAIL_DOMAIN)) {
      setStatus('error');
      setMsg(`Use seu email ${ALLOWED_EMAIL_DOMAIN}`);
      return;
    }
    try {
      const origin = typeof window !== 'undefined' ? window.location.origin : '';
      const { error } = await getSupabaseBrowser().auth.signInWithOtp({
        email: cleanEmail,
        options: {
          emailRedirectTo: `${origin}/auth/callback?redirect=${encodeURIComponent(redirect)}`,
        },
      });
      if (error) throw error;
      setStatus('sent');
      setMsg('Link enviado! Verifique sua caixa de entrada.');
    } catch (err) {
      setStatus('error');
      setMsg(err instanceof Error ? err.message : 'Erro ao enviar link');
    }
  }

  return (
    <main style={styles.main}>
      <div style={styles.card}>
        <div style={styles.eyebrow}>ZZYON Docs</div>
        <h1 style={styles.title}>Acesso restrito</h1>
        <p style={styles.subtitle}>
          Documentação operacional ZZYON — exclusiva para contas <strong>{ALLOWED_EMAIL_DOMAIN}</strong>
        </p>

        {reason === 'wrong-domain' && (
          <div style={{ ...styles.alert, ...styles.alertWarn }}>
            Você está logado com um email fora de {ALLOWED_EMAIL_DOMAIN}. Faça login com o email Ícaro.
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={`voce${ALLOWED_EMAIL_DOMAIN}`}
            required
            style={styles.input}
            autoFocus
          />
          <button type="submit" style={styles.button} disabled={status === 'sending'}>
            {status === 'sending' ? 'Enviando...' : 'Receber Magic Link por email'}
          </button>
        </form>

        {msg && (
          <div
            style={{
              ...styles.alert,
              ...(status === 'sent' ? styles.alertOk : status === 'error' ? styles.alertErr : {}),
            }}
          >
            {msg}
          </div>
        )}

        <div style={styles.foot}>
          <a href="/" style={styles.link}>← Voltar ao início</a>
        </div>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<main style={styles.main}><div style={styles.card}>Carregando...</div></main>}>
      <LoginContent />
    </Suspense>
  );
}

const styles: Record<string, React.CSSProperties> = {
  main: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
    background: '#05081C',
  },
  card: {
    width: '100%',
    maxWidth: 440,
    background: 'rgba(10,14,39,0.72)',
    border: '1px solid rgba(59,110,255,0.18)',
    borderRadius: 18,
    padding: '48px 36px',
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    color: '#F5F7FA',
    fontFamily: "'Inter','Helvetica Neue',Arial,sans-serif",
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: '0.14em',
    textTransform: 'uppercase',
    color: '#3B6EFF',
    marginBottom: 8,
  },
  title: {
    fontSize: 24,
    fontWeight: 600,
    margin: '0 0 8px 0',
    letterSpacing: '-0.01em',
  },
  subtitle: {
    fontSize: 13,
    color: 'rgba(245,247,250,0.6)',
    lineHeight: 1.5,
    marginBottom: 28,
  },
  input: {
    width: '100%',
    boxSizing: 'border-box',
    padding: '13px 16px',
    borderRadius: 8,
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.08)',
    color: '#F5F7FA',
    fontSize: 14,
    outline: 'none',
  },
  button: {
    width: '100%',
    padding: '12px 18px',
    borderRadius: 8,
    background: '#3B6EFF',
    color: '#FFFFFF',
    border: '0',
    fontWeight: 600,
    fontSize: 14,
    cursor: 'pointer',
  },
  alert: {
    marginTop: 14,
    padding: '10px 12px',
    borderRadius: 6,
    fontSize: 12,
    lineHeight: 1.5,
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.06)',
  },
  alertOk: {
    background: 'rgba(34,197,94,0.08)',
    borderColor: 'rgba(34,197,94,0.3)',
    color: '#22C55E',
  },
  alertWarn: {
    background: 'rgba(245,158,11,0.08)',
    borderColor: 'rgba(245,158,11,0.3)',
    color: '#F59E0B',
    marginBottom: 16,
    marginTop: 0,
  },
  alertErr: {
    background: 'rgba(239,68,68,0.08)',
    borderColor: 'rgba(239,68,68,0.3)',
    color: '#EF4444',
  },
  foot: {
    marginTop: 24,
    textAlign: 'center',
    fontSize: 12,
  },
  link: {
    color: 'rgba(245,247,250,0.6)',
    textDecoration: 'none',
  },
};
