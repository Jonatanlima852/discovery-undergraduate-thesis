async function request(path) {
  const response = await fetch(path, { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `A API respondeu ${response.status}.`);
  }
  return response.json();
}

export const inspectorApi = {
  async listRuns() {
    return (await request('/api/runs')).runs;
  },
  async getRun(runId) {
    return request(`/api/runs/${encodeURIComponent(runId)}`);
  },
};
