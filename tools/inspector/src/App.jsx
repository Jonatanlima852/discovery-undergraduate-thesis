import { useCallback, useEffect, useState } from 'react';
import { inspectorApi } from './api.js';
import Overview from './components/Overview.jsx';
import RawData from './components/RawData.jsx';
import Results from './components/Results.jsx';
import RunBrowser from './components/RunBrowser.jsx';
import Sidebar from './components/Sidebar.jsx';
import Timeline from './components/Timeline.jsx';
import { Footer, TopBar } from './components/TopBar.jsx';

export default function App() {
  const [runs, setRuns] = useState([]);
  const [report, setReport] = useState(null);
  const [origin, setOrigin] = useState('');
  const [active, setActive] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true); setError('');
    try { setRuns(await inspectorApi.listRuns()); }
    catch (failure) { setRuns([]); setError(failure.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const showReport = (files, label) => {
    setReport(window.TGInspector.parse(files));
    setOrigin(label); setActive('overview'); setError('');
  };

  const selectRun = async runId => {
    setDetailLoading(true); setError('');
    try {
      const detail = await inspectorApi.getRun(runId);
      showReport(detail.files, `EXECUÇÃO ${runId}`);
    } catch (failure) { setError(failure.message); }
    finally { setDetailLoading(false); }
  };

  const reset = () => { setReport(null); setActive('overview'); refresh(); };
  const openSample = () => showReport(window.TGInspectorSample.files, window.TGInspectorSample.label);

  if (!report) return <div className="app-shell"><TopBar/><RunBrowser runs={runs} loading={loading} error={error} onRefresh={refresh} onSelect={selectRun} onSample={openSample}/>{detailLoading && <div className="loading-overlay"><span className="spinner"/><strong>Abrindo execução…</strong></div>}<Footer/></div>;

  return <div className="app-shell report-shell"><TopBar onReset={reset}/><div className="workspace"><Sidebar active={active} onChange={setActive} report={report}/><main className="report-main">{active === 'overview' && <Overview report={report} origin={origin}/>} {active === 'results' && <Results report={report}/>} {active === 'timeline' && <Timeline report={report}/>} {active === 'raw' && <RawData report={report}/>}</main></div></div>;
}
