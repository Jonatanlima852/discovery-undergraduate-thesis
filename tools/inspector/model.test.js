'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {parse, filterEvents} = require('./model.js');
const sample = require('./sample.js');
const file = (name, value) => ({name, content: typeof value === 'string' ? value : JSON.stringify(value)});

test('recorded recovery preserves failed attempt and successful agent, separating SDK events', () => {
  const report = parse(sample.files);
  assert.equal(report.status, 'COMPLETED');
  assert.equal(report.rows[0].agent_id, 'b-healthy');
  assert.equal(report.events.length, 7);
  assert.deepEqual(report.warnings, []);
  assert.deepEqual(filterEvents(report.events, '', 'events.jsonl').map(event => event.type),
    ['TASK_CREATED', 'TASK_ASSIGNED', 'TASK_TIMEOUT', 'TASK_REASSIGNED', 'TASK_COMPLETED']);
  assert.equal(filterEvents(report.events, 'A-SLOW', '').length, 2);
  assert.equal(filterEvents(report.events, 'TASK_TIMEOUT', 'result.json (SDK)').length, 0);
});
test('workflow retains pending steps without result and domain evaluation', () => {
  const report = parse([file('result.json', {workflow_id: 'flow', steps: {
    first: {status: 'COMPLETED', duration_ms: 10, result: {agent_id: 'bdi', output: {route: ['A', 'D']}}},
    second: {status: 'PENDING', result: null}}}), file('result.evaluation.json', {valid: false})]);
  assert.equal(report.kind, 'Workflow');
  assert.equal(report.rows.length, 2);
  assert.equal(report.rows[1].status, 'PENDING');
  assert.equal(report.rows[1].agent_id, undefined);
  assert.equal(report.data['result.evaluation.json'].valid, false);
  assert.equal(report.status, 'NÃO INFORMADO');
});
test('message preserves correlation and participants', () => {
  const report = parse([file('result.json', {message_id: 'm', sender_id: 'a', receiver_id: 'b', correlation_id: 'c'})]);
  assert.equal(report.kind, 'Mensagem');
  assert.equal(report.result.correlation_id, 'c');
  assert.deepEqual(report.rows, []);
});
test('failure before result remains visible and does not infer completion', () => {
  const report = parse([file('status', 'FAILED'), file('summary.json', {status: 'FAILED', error: 'timeout'})]);
  assert.equal(report.status, 'FAILED');
  assert.equal(report.summary.error, 'timeout');
  assert.match(report.warnings[0], /result.json ausente/);
  assert.equal(report.kind, 'Sem resultado');
});
test('executor cancellation takes precedence over successful client summary', () => {
  const report = parse([file('status', 'CANCELLED'), file('summary.json', {status: 'COMPLETED'})]);
  assert.equal(report.status, 'CANCELLED');
  assert.ok(report.warnings.some(value => value.includes('difere')));
});
test('malformed JSONL preserves valid events and reports skipped lines', () => {
  const report = parse([file('events.jsonl', '{"type":"A"}\ninvalid\nnull\n[]\n{"type":"B"}\n')]);
  assert.deepEqual(report.events.map(event => event.type), ['A', 'B']);
  assert.deepEqual(report.events.map(event => event.line), [1, 5]);
  assert.match(report.warnings[0], /3 linha/);
});
test('mixed traces remain visible with warning and timestamps sort stably', () => {
  const report = parse([file('result.json', {results: {}, trace_id: 'one'}), file('events.jsonl', [
    {type: 'SECOND', timestamp: '2026-10-08T00:00:02Z', trace_id: 'two'},
    {type: 'UNKNOWN', timestamp: 'invalid'},
    {type: 'FIRST', timestamp: '2026-10-08T00:00:01Z', trace_id: 'one'},
  ].map(value => JSON.stringify(value)).join('\n'))]);
  assert.deepEqual(report.events.map(event => event.type), ['FIRST', 'SECOND', 'UNKNOWN']);
  assert.ok(report.warnings.some(value => value.includes('trace diferente')));
});
test('duplicate files and mixed folders cannot silently overwrite an execution', () => {
  assert.throws(() => parse([file('status', 'FAILED'), file('status', 'COMPLETED')]), /repetido/);
  assert.throws(() => parse([{...file('status', 'FAILED'), path: 'run-a/status'},
    {...file('scenario', 'demo'), path: 'run-b/scenario'}]), /pastas diferentes/);
});
test('invalid JSON fails clearly; unsupported structures are not called successful', () => {
  for (const content of ['null', '[]', '{']) assert.throws(() => parse([file('result.json', content)]), /objeto JSON/);
  assert.throws(() => parse([file('build.log', 'log')]), /Nenhum arquivo reconhecido/);
  const report = parse([file('result.json', {strategies: {}})]);
  assert.equal(report.status, 'NÃO INFORMADO');
  assert.ok(report.warnings.some(value => value.includes('não reconhecido')));
});
test('imported markup remains plain data', () => {
  const attack = '<img src=x onerror=alert(1)>';
  const report = parse([file('scenario', attack), file('result.json', {results: {test: {output: attack}}})]);
  assert.equal(report.scenario, attack);
  assert.equal(report.rows[0].output, attack);
});
