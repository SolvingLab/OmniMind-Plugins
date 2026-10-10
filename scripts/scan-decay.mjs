import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { GitHub, ROOT, DAY, NAME_PATTERN, sourceKey, decayKey, readJson, writeJson } from './lib/github.mjs';

export const STATE_FILE = resolve(ROOT, 'data/decay-state.json');

export async function loadDecayState(file = STATE_FILE) {
  const value = await readJson(file, { version: 1, entries: {} });
  if (value.version !== 1 || !value.entries || typeof value.entries !== 'object' || Array.isArray(value.entries)) throw new Error('Invalid decay-state.json schema');
  for (const [key, entry] of Object.entries(value.entries)) {
    if (!['hidden', 'removed'].includes(entry.status) || !Array.isArray(entry.subjects) || !Array.isArray(entry.reasons) ||
      (entry.hiddenSince && !Number.isFinite(Date.parse(entry.hiddenSince)))) throw new Error(`Invalid decay state: ${key}`);
  }
  return value;
}

export function decayDecision(meta, current, name, previous, now = new Date()) {
  let immediate;
  if (meta.notFound) immediate = 'not_found';
  else if (meta.private) immediate = 'private_repository';
  else if (meta.archived) immediate = 'archived';
  else if (!meta.sha || current?.error) immediate = current?.error ?? 'unsupported_manifest';
  else if (!NAME_PATTERN.test(current?.manifest?.name ?? '')) immediate = 'invalid_manifest_name';
  else if (current.manifest.name !== name) immediate = 'name_mismatch';
  if (immediate) return { status: 'removed', reasons: [immediate], removedSince: previous?.removedSince ?? now.toISOString() };
  const reasons = [];
  if (!Number.isFinite(Date.parse(meta.pushedAt))) throw new Error(`Invalid pushedAt metadata: ${meta.repo}`);
  if ((now.getTime() - Date.parse(meta.pushedAt)) / DAY > 180) reasons.push('pushed_over_180_days');
  if (!Number.isFinite(meta.stars)) throw new Error(`Invalid star metadata: ${meta.repo}`);
  if (meta.stars < 400) reasons.push('stars_below_400');
  if (!reasons.length) return { status: 'healthy', reasons: [] };
  const hiddenSince = previous?.hiddenSince ?? now.toISOString();
  const removed = now.getTime() - Date.parse(hiddenSince) >= 7 * DAY;
  return { status: removed ? 'removed' : 'hidden', reasons, hiddenSince,
    ...(removed ? { removedSince: previous?.removedSince ?? now.toISOString() } : {}) };
}

export async function evaluateDecay(subjects, client, { state, now = new Date() }) {
  const unique = [...new Map(subjects.map(s => [`${s.id}:${sourceKey(s.entry.source)}:${s.entry.name}`, s])).values()];
  await client.metadataBatch(unique.map(s => s.entry.source.repo));
  const heads = unique.flatMap(s => {
    const meta = client.meta.get(s.entry.source.repo.toLowerCase());
    return !meta.notFound && !meta.private && !meta.archived && meta.sha ? [{ ...s.entry.source, repo: meta.repo, sha: meta.sha }] : [];
  });
  const manifests = await client.manifests(heads);
  const entries = structuredClone(state.entries);
  const byKey = new Map();
  for (const subject of unique) {
    const key = decayKey(subject.entry.source);
    if (!byKey.has(key)) byKey.set(key, []);
    byKey.get(key).push(subject);
  }
  const findings = [];
  const decisions = new Map();
  for (const [key, group] of byKey) {
    const source = group[0].entry.source;
    const meta = client.meta.get(source.repo.toLowerCase());
    const current = meta.sha ? manifests.get(sourceKey({ ...source, repo: meta.repo, sha: meta.sha })) : undefined;
    const results = group.map(subject => ({ subject, ...decayDecision(meta, current, subject.entry.name, state.entries[key], now) }));
    // A repository/path can have multiple pinned versions; mismatch affects
    // only that version's entry, rather than hiding a healthy sibling name.
    for (const result of results) decisions.set(`${result.subject.id}:${sourceKey(result.subject.entry.source)}:${result.subject.entry.name}`, result);
    const unhealthy = results.filter(r => r.status !== 'healthy');
    if (!unhealthy.length) delete entries[key];
    else {
      const representative = unhealthy.find(r => r.status === 'hidden') ?? unhealthy[0];
      entries[key] = { status: representative.status, reasons: representative.reasons,
        ...(representative.hiddenSince ? { hiddenSince: representative.hiddenSince } : {}),
        ...(representative.removedSince ? { removedSince: representative.removedSince } : {}),
        subjects: unhealthy.map(r => r.subject) };
    }
    findings.push(...results.map(({ subject, ...decision }) => ({ id: subject.id, name: subject.entry.name, source: subject.entry.source, ...decision })));
  }
  const nextState = { version: 1, entries: Object.fromEntries(Object.entries(entries).sort(([a], [b]) => a.localeCompare(b))) };
  return { state: nextState, decisions, findings, summary: {
    checked: findings.length,
    healthy: findings.filter(f => f.status === 'healthy').length,
    hidden: findings.filter(f => f.status === 'hidden').length,
    removed: findings.filter(f => f.status === 'removed').length,
    recovered: Object.keys(state.entries).filter(key => !nextState.entries[key]).length,
  } };
}

export async function scanDecay({ dryRun = false, client = new GitHub(), now = new Date() } = {}) {
  const state = await loadDecayState();
  const subjects = Object.values(state.entries).flatMap(e => e.subjects);
  for (const id of ['anthropic', 'openai', 'zcode', 'solvinglab', 'community']) {
    const market = await readJson(resolve(ROOT, `dist/marketplaces/${id}.json`), { plugins: [] });
    subjects.push(...market.plugins.map(entry => ({ id, entry })));
  }
  if (!subjects.length) throw new Error('No built entries or decay records; run npm run build first');
  const result = await evaluateDecay(subjects, client, { state, now });
  console.log(JSON.stringify({ dryRun, ...result.summary, findings: result.findings.filter(f => f.status !== 'healthy') }, null, 2));
  if (!dryRun) {
    await writeJson(STATE_FILE, result.state);
    // Rebuild every view so scan-decay alone applies the decisions immediately.
    const { build } = await import('./build.mjs');
    await build({ client, now });
  }
  return result;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const args = process.argv.slice(2);
  if (args.some(arg => arg !== '--dry-run')) { console.error('Usage: node scripts/scan-decay.mjs [--dry-run]'); process.exitCode = 1; }
  else scanDecay({ dryRun: args.includes('--dry-run') }).catch(error => { console.error(error.message); process.exitCode = 1; });
}
