import { JsonDetails } from './ui.jsx';

export default function RawData({ report }) {
  const eventFiles = ['events.jsonl', 'message-events.jsonl'].filter(name => report.names.includes(name));
  return <section className="content-card"><div className="section-heading"><div><span className="kicker">AUDITORIA</span><h2>Dados brutos</h2></div></div><p className="section-note">Conteúdo original interpretado pelo visualizador. Logs de construção e serviços permanecem na pasta da execução.</p><div className="raw-grid">{Object.entries(report.data).map(([name, data]) => <JsonDetails key={name} title={name} data={data}/>)}{eventFiles.map(name => <JsonDetails key={name} title={`${name} · eventos válidos`} data={report.events.filter(event => event.source === name).map(({ source, line, ...event }) => event)}/>)}</div></section>;
}
