import Link from 'next/link';

const torres = [
  { name: 'Torre de Saúde', url: 'https://saude.zzyon.com', desc: 'Observabilidade dos agentes, infra e custos LLM' },
  { name: 'Torre RA1000', url: 'https://ra.zzyon.com', desc: 'Pulso Reclame Aqui + escalação automática' },
  { name: 'Torre Frota', url: 'https://frota.zzyon.com', desc: 'GPS, escala motoristas, eventos operacionais' },
  { name: 'Torre Controladoria', url: 'https://controladoria.zzyon.com', desc: 'DRE, custos por filial, formação de preço' },
  { name: 'Torre Cargas', url: 'https://cargas.zzyon.com', desc: 'Rastreio CTe, ocorrências, SLA' },
  { name: 'Torre Comercial', url: 'https://comercial.zzyon.com', desc: 'Pipeline, propostas, carteira' },
  { name: 'Torre Inbox', url: 'https://inbox.zzyon.com', desc: 'Multi-canal unificado (WhatsApp/Email/RA)' },
  { name: 'Torre Briefing', url: 'https://briefing.zzyon.com', desc: 'Resumo diário pro Roberval' },
];

const agentes = [
  { name: 'Cláudio', papel: 'Atendimento WhatsApp + roteamento intent', stack: 'Haiku 4.5 + Sonnet 4.6' },
  { name: 'RA1000', papel: 'Reclame Aqui (varredura, replica, SLA)', stack: 'Sonnet 4.6 + GPT-4o fallback' },
  { name: 'Roberval', papel: 'Briefing diário CEO', stack: 'Sonnet 4.6 + Perplexity Sonar' },
];

export default function HomePage() {
  return (
    <main className="flex-1 max-w-5xl mx-auto px-6 py-16">
      <div className="mb-12">
        <div className="zzy-eyebrow mb-3">ZZYON · Inteligência em órbita</div>
        <h1 className="text-5xl font-bold mb-4 tracking-tight">Plataforma ZZYON</h1>
        <p className="text-lg text-fd-muted-foreground max-w-2xl">
          Documentação viva da plataforma de IA da Ícaro Express — agentes, torres operacionais,
          arquitetura multi-LLM, infraestrutura e runbooks.
        </p>
        <div className="flex gap-3 mt-6">
          <Link
            href="/docs"
            className="px-5 py-2.5 rounded-lg bg-fd-primary text-fd-accent-foreground font-medium hover:opacity-90 transition"
          >
            Abrir documentação →
          </Link>
          <a
            href="https://github.com/ZZYONBR/zyon-docs"
            className="px-5 py-2.5 rounded-lg border border-fd-border hover:bg-fd-muted transition"
          >
            GitHub
          </a>
        </div>
      </div>

      <section className="mb-12">
        <div className="zzy-eyebrow mb-3">Torres operacionais</div>
        <h2 className="text-2xl font-semibold mb-6">8 painéis em produção</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {torres.map((t) => (
            <a
              key={t.url}
              href={t.url}
              target="_blank"
              rel="noopener"
              className="block p-4 rounded-lg border border-fd-border hover:border-fd-primary/40 hover:bg-fd-muted transition"
            >
              <div className="font-medium">{t.name}</div>
              <div className="text-sm text-fd-muted-foreground mt-1">{t.desc}</div>
              <div className="text-xs text-fd-primary mt-2 font-mono">{t.url.replace('https://', '')}</div>
            </a>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <div className="zzy-eyebrow mb-3">Agentes ativos</div>
        <h2 className="text-2xl font-semibold mb-6">3 agentes LLM em produção</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {agentes.map((a) => (
            <div key={a.name} className="p-4 rounded-lg border border-fd-border">
              <div className="font-medium text-fd-primary">{a.name}</div>
              <div className="text-sm mt-1">{a.papel}</div>
              <div className="text-xs text-fd-muted-foreground mt-2 font-mono">{a.stack}</div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <div className="zzy-eyebrow mb-3">Sobre esta documentação</div>
        <p className="text-sm text-fd-muted-foreground max-w-2xl">
          Este site é gerado a partir de Markdown versionado em{' '}
          <code className="text-fd-foreground">ZZYONBR/zyon-docs</code>. Um agente{' '}
          <strong className="text-fd-foreground">doc-auditor</strong> roda semanalmente para detectar
          divergências entre o código e a documentação, e abre PRs com patches propostos.
        </p>
      </section>
    </main>
  );
}
