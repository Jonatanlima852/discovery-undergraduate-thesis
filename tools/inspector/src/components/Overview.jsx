import { Icon, StatusBadge, display, formatMs } from './ui.jsx';

function MetricCard({ icon, label, children, accent }) {
  return <article className={`metric-card ${accent || ''}`}><div className="metric-icon"><Icon name={icon}/></div><div><span>{label}</span><strong>{children}</strong></div></article>;
}

export default function Overview({ report, origin }) {
  return <>
    <section className="hero-card"><div><span className="kicker">{origin}</span><h1>{report.scenario}</h1><p>Snapshot de evidências da execução. Os valores vêm dos arquivos registrados, não de serviços ativos.</p></div><StatusBadge status={report.status}/></section>
    <section className="metrics-grid"><MetricCard icon="activity" label="Estado" accent="green">{report.status}</MetricCard><MetricCard icon="layers" label="Resultado">{report.kind}</MetricCard><MetricCard icon="clock" label="Duração total">{formatMs(report.summary.elapsed_ms)}</MetricCard><MetricCard icon="file" label="Eventos">{report.events.length}</MetricCard></section>
    <section className="context-strip"><div><span>Trace ID</span><code>{display(report.trace)}</code></div><div><span>Ambiente</span><strong>{display(report.environment)}</strong></div><div><span>Arquivos</span><strong>{report.names.length} reconhecidos</strong></div></section>
    {report.summary.error && <p className="error-message"><Icon name="warning"/>{report.summary.error}</p>}
    {!!report.warnings.length && <section className="warning-list"><h2><Icon name="warning"/>Pontos de atenção</h2>{report.warnings.map((warning, index) => <p key={index}>{warning}</p>)}</section>}
  </>;
}
