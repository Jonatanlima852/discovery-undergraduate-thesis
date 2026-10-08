import { useMemo, useState } from 'react';
import { Icon, JsonDetails, display } from './ui.jsx';

const PAGE_SIZE = 25;

export default function Timeline({ report }) {
  const [query, setQuery] = useState('');
  const [source, setSource] = useState('');
  const [page, setPage] = useState(0);
  const sources = useMemo(() => [...new Set(report.events.map(event => event.source))], [report.events]);
  const events = useMemo(() => window.TGInspector.filterEvents(report.events, query, source), [report.events, query, source]);
  const pages = Math.max(1, Math.ceil(events.length / PAGE_SIZE));
  const safePage = Math.min(page, pages - 1);
  const visible = events.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);
  const changeFilter = setter => event => { setter(event.target.value); setPage(0); };
  return <section className="content-card">
    <div className="section-heading"><div><span className="kicker">EVIDÊNCIAS</span><h2>Linha do tempo</h2></div><span className="count">{events.length} de {report.events.length}</span></div>
    <div className="toolbar"><label className="search-box"><Icon name="search"/><input type="search" value={query} onChange={changeFilter(setQuery)} placeholder="Buscar evento, agente, task ou trace…"/></label><select value={source} onChange={changeFilter(setSource)} aria-label="Filtrar por fonte"><option value="">Todas as fontes</option>{sources.map(item => <option key={item}>{item}</option>)}</select></div>
    <div className="timeline">{visible.map((event, index) => <article className="timeline-item" key={`${event.source}-${event.line}-${index}`}><div className="timeline-marker"><span/></div><div className="event-card"><div className="event-top"><strong>{event.type}</strong><time>{display(event.timestamp)}</time></div><div className="event-route"><span>{event.agent_id || 'runtime'}</span>{(event.step_id || event.step) && <><Icon name="arrow" size={14}/><span>{event.step_id || event.step}</span></>}</div><div className="event-ids">{['task_id', 'trace_id', 'workflow_id', 'run_id', 'details'].map(key => event[key] && <span key={key}><small>{key}</small>{String(event[key])}</span>)}</div><JsonDetails title={`${event.source} · linha ${event.line}`} data={event}/></div></article>)}{!visible.length && <div className="no-data">Nenhum evento corresponde aos filtros.</div>}</div>
    <div className="pager"><button disabled={safePage === 0} onClick={() => setPage(safePage - 1)}>Anterior</button><span>{safePage + 1} / {pages}</span><button disabled={safePage >= pages - 1} onClick={() => setPage(safePage + 1)}>Próxima</button></div>
  </section>;
}
