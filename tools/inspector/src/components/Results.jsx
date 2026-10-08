import { Icon, JsonDetails, StatusBadge, display, formatMs } from './ui.jsx';

export default function Results({ report }) {
  return <section className="content-card">
    <div className="section-heading"><div><span className="kicker">RESULTADOS</span><h2>Etapas e participantes</h2></div><span className="count">{report.rows.length} etapas</span></div>
    <p className="section-note">A ordem visual segue o relatório e não representa, por si só, dependências de execução.</p>
    <div className="step-list">
      {report.rows.map((row, index) => <article className="step-card" key={`${row.name}-${index}`}><div className="step-index">{String(index + 1).padStart(2, '0')}</div><div className="step-body">
        <div className="step-title"><div><h3>{row.name}</h3><code>{display(row.task_id)}</code></div><StatusBadge status={row.status}/></div>
        <div className="step-meta"><span><small>Agente</small>{display(row.agent_id)}</span><span><small>Tipo</small>{display(row.agent_kind)}</span><span><small>Duração</small>{formatMs(row.duration_ms)}</span></div>
        {row.output !== undefined && <JsonDetails title="Saída da etapa" data={row.output}/>} {row.error && <JsonDetails title="Erro da tarefa" data={row.error} open/>}
      </div></article>)}
      {!report.rows.length && report.kind !== 'Mensagem' && <div className="no-data">Nenhuma tarefa ou etapa disponível nesta execução.</div>}
      {report.kind === 'Mensagem' && <article className="message-card"><div className="message-route"><strong>{display(report.result.sender_id)}</strong><Icon name="arrow"/><strong>{display(report.result.receiver_id)}</strong></div><div className="step-meta"><span><small>Mensagem</small>{display(report.result.message_id)}</span><span><small>Conversa</small>{display(report.result.conversation_id)}</span><span><small>Correlação</small>{display(report.result.correlation_id)}</span></div><JsonDetails title="Payload" data={report.result.payload}/></article>}
    </div>
    {report.result.output !== undefined && <JsonDetails title="Saída agregada do workflow" data={report.result.output}/>} {report.result.error && <JsonDetails title="Erro do workflow" data={report.result.error} open/>} {report.data['result.evaluation.json'] && <JsonDetails title="Avaliação do domínio" data={report.data['result.evaluation.json']}/>} 
  </section>;
}
