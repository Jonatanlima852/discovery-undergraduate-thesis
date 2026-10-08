import { useMemo, useRef, useState } from 'react';

const PAGE_SIZE = 25;
const MAX_BYTES = 20 * 1024 * 1024;

const Icon = ({ name, size = 18 }) => {
  const paths = {
    upload: <><path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M5 20h14"/></>,
    play: <path d="m8 5 11 7-11 7Z"/>,
    activity: <><path d="M3 12h4l2-7 4 14 2-7h6"/></>,
    layers: <><path d="m12 3-9 5 9 5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 16 9 5 9-5"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    warning: <><path d="M12 3 2.8 20h18.4Z"/><path d="M12 9v4M12 17h.01"/></>,
    file: <><path d="M6 2h8l4 4v16H6Z"/><path d="M14 2v5h5"/></>,
    arrow: <path d="m9 18 6-6-6-6"/>,
    terminal: <><rect x="3" y="4" width="18" height="16" rx="2"/><path d="m7 9 3 3-3 3M13 15h4"/></>,
  };
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
};

const value = input => input == null || input === '' ? 'Não informado' : String(input);
const formatMs = input => typeof input === 'number' && Number.isFinite(input)
  ? `${input.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} ms` : '—';

function StatusBadge({ status }) {
  const normalized = value(status).toUpperCase();
  const tone = normalized.includes('COMPLETED') ? 'success'
    : normalized.includes('FAIL') || normalized.includes('CANCEL') ? 'danger'
      : normalized.includes('RUN') || normalized.includes('PROGRESS') ? 'active' : 'neutral';
  return <span className={`badge ${tone}`}><span className="badge-dot" />{value(status)}</span>;
}

function JsonDetails({ title, data, open = false }) {
  return <details className="json-details" open={open}>
    <summary>{title}<Icon name="arrow" size={15} /></summary>
    <pre>{JSON.stringify(data, null, 2)}</pre>
  </details>;
}

function EmptyState({ onPick, onSample, busy, error, inputRef, onFiles }) {
  const [dragging, setDragging] = useState(false);
  return <main className="empty-layout">
    <section className="welcome-copy">
      <span className="kicker">INSPECTOR LOCAL</span>
      <h1>Entenda uma execução<br/><em>sem decifrar logs.</em></h1>
      <p>Carregue as evidências produzidas pelo executor e navegue por tarefas, agentes e eventos em uma visão única.</p>
      <div className="privacy-note"><Icon name="check" /><span>Processamento 100% local. Nenhum arquivo sai do navegador.</span></div>
    </section>
    <section className="import-panel">
      <div className={`drop-zone ${dragging ? 'dragging' : ''}`}
        onDragOver={event => { event.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={event => { event.preventDefault(); setDragging(false); onFiles([...event.dataTransfer.files]); }}>
        <div className="upload-icon"><Icon name="upload" size={27} /></div>
        <h2>{busy ? 'Lendo evidências…' : 'Abra uma execução'}</h2>
        <p>Arraste os arquivos de uma pasta <code>.tg/runs/ID</code> ou escolha manualmente.</p>
        <button className="primary" onClick={onPick} disabled={busy}><Icon name="file" />Selecionar arquivos</button>
        <input ref={inputRef} type="file" multiple hidden onChange={event => onFiles([...event.target.files])}/>
        <span className="file-hint">JSON, JSONL e metadados · até 20 MB</span>
      </div>
      <div className="sample-row">
        <div><strong>Quer apenas explorar?</strong><span>Use uma execução real já incluída.</span></div>
        <button className="secondary" onClick={onSample}><Icon name="play" />Abrir exemplo</button>
      </div>
      {error && <p className="error-message"><Icon name="warning" />{error}</p>}
    </section>
  </main>;
}

function MetricCard({ icon, label, children, accent }) {
  return <article className={`metric-card ${accent || ''}`}>
    <div className="metric-icon"><Icon name={icon} /></div>
    <div><span>{label}</span><strong>{children}</strong></div>
  </article>;
}

function Overview({ report, origin }) {
  const elapsed = report.summary.elapsed_ms;
  return <>
    <section className="hero-card">
      <div>
        <span className="kicker">{origin}</span>
        <h1>{report.scenario}</h1>
        <p>Snapshot de evidências da execução. Os valores abaixo vêm dos arquivos selecionados, não de serviços ativos.</p>
      </div>
      <StatusBadge status={report.status} />
    </section>
    <section className="metrics-grid">
      <MetricCard icon="activity" label="Estado" accent="green">{report.status}</MetricCard>
      <MetricCard icon="layers" label="Resultado">{report.kind}</MetricCard>
      <MetricCard icon="clock" label="Duração total">{formatMs(elapsed)}</MetricCard>
      <MetricCard icon="file" label="Eventos">{report.events.length}</MetricCard>
    </section>
    <section className="context-strip">
      <div><span>Trace ID</span><code>{value(report.trace)}</code></div>
      <div><span>Ambiente</span><strong>{value(report.environment)}</strong></div>
      <div><span>Arquivos</span><strong>{report.names.length} reconhecidos</strong></div>
    </section>
    {report.summary.error && <p className="error-message"><Icon name="warning" />{report.summary.error}</p>}
    {!!report.warnings.length && <section className="warning-list">
      <h2><Icon name="warning" />Pontos de atenção</h2>
      {report.warnings.map((warning, index) => <p key={index}>{warning}</p>)}
    </section>}
  </>;
}

function Results({ report }) {
  return <section className="content-card">
    <div className="section-heading"><div><span className="kicker">RESULTADOS</span><h2>Etapas e participantes</h2></div><span className="count">{report.rows.length} etapas</span></div>
    <p className="section-note">A ordem visual segue o relatório e não representa, por si só, dependências de execução.</p>
    <div className="step-list">
      {report.rows.map((row, index) => <article className="step-card" key={`${row.name}-${index}`}>
        <div className="step-index">{String(index + 1).padStart(2, '0')}</div>
        <div className="step-body">
          <div className="step-title"><div><h3>{row.name}</h3><code>{value(row.task_id)}</code></div><StatusBadge status={row.status} /></div>
          <div className="step-meta">
            <span><small>Agente</small>{value(row.agent_id)}</span>
            <span><small>Tipo</small>{value(row.agent_kind)}</span>
            <span><small>Duração</small>{formatMs(row.duration_ms)}</span>
          </div>
          {row.output !== undefined && <JsonDetails title="Saída da etapa" data={row.output} />}
          {row.error && <JsonDetails title="Erro da tarefa" data={row.error} open />}
        </div>
      </article>)}
      {!report.rows.length && report.kind !== 'Mensagem' && <div className="no-data">Nenhuma tarefa ou etapa disponível nesta execução.</div>}
      {report.kind === 'Mensagem' && <article className="message-card">
        <div className="message-route"><strong>{value(report.result.sender_id)}</strong><Icon name="arrow"/><strong>{value(report.result.receiver_id)}</strong></div>
        <div className="step-meta"><span><small>Mensagem</small>{value(report.result.message_id)}</span><span><small>Conversa</small>{value(report.result.conversation_id)}</span><span><small>Correlação</small>{value(report.result.correlation_id)}</span></div>
        <JsonDetails title="Payload" data={report.result.payload} />
      </article>}
    </div>
    {report.result.output !== undefined && <JsonDetails title="Saída agregada do workflow" data={report.result.output} />}
    {report.result.error && <JsonDetails title="Erro do workflow" data={report.result.error} open />}
    {report.data['result.evaluation.json'] && <JsonDetails title="Avaliação do domínio" data={report.data['result.evaluation.json']} />}
  </section>;
}

function Timeline({ report }) {
  const [query, setQuery] = useState('');
  const [source, setSource] = useState('');
  const [page, setPage] = useState(0);
  const sources = useMemo(() => [...new Set(report.events.map(event => event.source))], [report]);
  const events = useMemo(() => window.TGInspector.filterEvents(report.events, query, source), [report, query, source]);
  const pages = Math.max(1, Math.ceil(events.length / PAGE_SIZE));
  const safePage = Math.min(page, pages - 1);
  const visible = events.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);
  const changeFilter = setter => event => { setter(event.target.value); setPage(0); };
  return <section className="content-card">
    <div className="section-heading"><div><span className="kicker">EVIDÊNCIAS</span><h2>Linha do tempo</h2></div><span className="count">{events.length} de {report.events.length}</span></div>
    <div className="toolbar">
      <label className="search-box"><Icon name="search"/><input type="search" value={query} onChange={changeFilter(setQuery)} placeholder="Buscar evento, agente, task ou trace…"/></label>
      <select value={source} onChange={changeFilter(setSource)} aria-label="Filtrar por fonte"><option value="">Todas as fontes</option>{sources.map(item => <option key={item}>{item}</option>)}</select>
    </div>
    <div className="timeline">
      {visible.map((event, index) => <article className="timeline-item" key={`${event.source}-${event.line}-${index}`}>
        <div className="timeline-marker"><span /></div>
        <div className="event-card">
          <div className="event-top"><strong>{event.type}</strong><time>{value(event.timestamp)}</time></div>
          <div className="event-route"><span>{event.agent_id || 'runtime'}</span>{(event.step_id || event.step) && <><Icon name="arrow" size={14}/><span>{event.step_id || event.step}</span></>}</div>
          <div className="event-ids">
            {['task_id', 'trace_id', 'workflow_id', 'run_id', 'details'].map(key => event[key] && <span key={key}><small>{key}</small>{event[key]}</span>)}
          </div>
          <JsonDetails title={`${event.source} · linha ${event.line}`} data={event}/>
        </div>
      </article>)}
      {!visible.length && <div className="no-data">Nenhum evento corresponde aos filtros.</div>}
    </div>
    <div className="pager"><button disabled={safePage === 0} onClick={() => setPage(safePage - 1)}>Anterior</button><span>{safePage + 1} / {pages}</span><button disabled={safePage >= pages - 1} onClick={() => setPage(safePage + 1)}>Próxima</button></div>
  </section>;
}

function RawData({ report }) {
  const eventFiles = ['events.jsonl', 'message-events.jsonl'].filter(name => report.names.includes(name));
  return <section className="content-card">
    <div className="section-heading"><div><span className="kicker">AUDITORIA</span><h2>Dados brutos</h2></div></div>
    <p className="section-note">Conteúdo original interpretado pelo visualizador. Logs de construção e serviços permanecem na pasta da execução.</p>
    <div className="raw-grid">
      {Object.entries(report.data).map(([name, data]) => <JsonDetails key={name} title={name} data={data}/>) }
      {eventFiles.map(name => <JsonDetails key={name} title={`${name} · eventos válidos`} data={report.events.filter(event => event.source === name).map(({ source, line, ...event }) => event)}/>) }
    </div>
  </section>;
}

export default function App() {
  const [report, setReport] = useState(null);
  const [origin, setOrigin] = useState('');
  const [active, setActive] = useState('overview');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef(null);
  const load = (files, label) => {
    try {
      const parsed = window.TGInspector.parse(files);
      setReport(parsed); setOrigin(label); setActive('overview'); setError('');
    } catch (failure) { setReport(null); setError(failure.message || 'Não foi possível ler os arquivos.'); }
  };
  const readFiles = async selected => {
    const files = selected.filter(file => window.TGInspector.allowed.has(file.name));
    setBusy(true); setError('');
    try {
      if (!files.length) throw new Error('Nenhum arquivo reconhecido foi selecionado.');
      if (files.reduce((sum, file) => sum + file.size, 0) > MAX_BYTES) throw new Error('Seleção maior que 20 MB. Escolha uma execução menor.');
      const contents = await Promise.all(files.map(async file => ({ name: file.name, path: file.webkitRelativePath, content: await file.text() })));
      load(contents, 'ARQUIVOS LOCAIS');
    } catch (failure) { setReport(null); setError(failure.message); }
    finally { setBusy(false); }
  };
  const openSample = () => { if (inputRef.current) inputRef.current.value = ''; load(window.TGInspectorSample.files, window.TGInspectorSample.label); };
  if (!report) return <div className="app-shell"><TopBar/><EmptyState onPick={() => inputRef.current?.click()} onSample={openSample} busy={busy} error={error} inputRef={inputRef} onFiles={readFiles}/><Footer/></div>;
  const tabs = [{ id: 'overview', label: 'Visão geral', icon: 'activity' }, { id: 'results', label: 'Etapas', icon: 'layers' }, { id: 'timeline', label: 'Timeline', icon: 'clock' }, { id: 'raw', label: 'Dados brutos', icon: 'terminal' }];
  return <div className="app-shell report-shell">
    <TopBar onReset={() => setReport(null)} />
    <div className="workspace">
      <aside><span className="aside-label">NAVEGAÇÃO</span>{tabs.map(tab => <button key={tab.id} className={active === tab.id ? 'active' : ''} onClick={() => setActive(tab.id)}><Icon name={tab.icon}/>{tab.label}</button>)}<div className="aside-run"><small>EXECUÇÃO ATUAL</small><strong>{report.scenario}</strong><StatusBadge status={report.status}/></div></aside>
      <main className="report-main">
        {active === 'overview' && <Overview report={report} origin={origin}/>} 
        {active === 'results' && <Results report={report}/>} 
        {active === 'timeline' && <Timeline report={report}/>} 
        {active === 'raw' && <RawData report={report}/>} 
      </main>
    </div>
  </div>;
}

function TopBar({ onReset }) {
  return <header className="topbar"><div className="brand"><span className="brand-mark">TG</span><div><strong>Runtime Inspector</strong><small>evidências de execução</small></div></div>{onReset && <button className="new-run" onClick={onReset}><Icon name="upload"/>Abrir outra execução</button>}</header>;
}

function Footer() {
  return <footer><span>TG Runtime · protótipo de pesquisa</span><a href="../../docs/presentation.md">Roteiro de apresentação <Icon name="arrow" size={14}/></a></footer>;
}
