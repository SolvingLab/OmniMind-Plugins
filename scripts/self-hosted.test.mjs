import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { createListing, mergeMarkets, SOURCE_ORDER } from './build.mjs';
import { loadCategories } from './lib/categories.mjs';
import { evaluateDecay } from './scan-decay.mjs';
import { sourceKey } from './lib/github.mjs';

const fixture = resolve('scripts/fixtures/self-hosted');
const sha = 'a'.repeat(40);
const client = { file: async (_repo, _sha, path) => {
  try { return await readFile(resolve(fixture, path), 'utf8'); }
  catch (e) { if (e.code === 'ENOENT') return null; throw e; }
} };

test('self-hosted fixture produces pinned listing and rejects missing license', async () => {
  const { default: reader } = await import('./readers/self-hosted.mjs');
  const result = await reader(client, resolve(fixture, 'self-hosted.json'));
  assert.equal(result.candidates.length, 1);
  const record = result.candidates[0];
  assert.deepEqual(record.entry.source, { source: 'github', repo: 'SolvingLab/OmniMind-Plugins', path: 'plugins/example', sha });
  const manifest = JSON.parse(await client.file('', sha, 'plugins/example/.omnimind-plugin/plugin.json'));
  const listing = createListing({ ...record, source: record.entry.source }, { manifest, manifestPath: 'plugins/example/.omnimind-plugin/plugin.json' }, await loadCategories());
  assert.equal(listing.plugin.name, 'example');
  assert.deepEqual(listing.plugin.source, record.entry.source);
  assert.equal(result.rejections[0].reason, 'missing_license');
});

test('self-hosted decay checks pinned content rather than default branch', async () => {
  const source = { source: 'github', repo: 'SolvingLab/OmniMind-Plugins', path: 'plugins/example', sha };
  const fake = { meta: new Map([[source.repo.toLowerCase(), { repo: source.repo, sha: 'b'.repeat(40) }]]), metadataBatch: async () => {}, manifests: async sources => new Map(sources.map(s => [sourceKey(s), s.sha === sha ? { manifest: { name: 'example' } } : { error: 'unsupported_manifest' }])) };
  const result = await evaluateDecay([{ id: 'self-hosted', entry: { name: 'example', source } }], fake, { state: { entries: {} } });
  assert.equal(result.summary.healthy, 1);
});

test('self-hosted wins duplicate names', () => {
  const markets = Object.fromEntries(SOURCE_ORDER.map(id => [id, { plugins: [] }]));
  const plugin = (id) => ({ name: 'context7', source: { repo: id }, 'x-omnimind': {} });
  markets.anthropic.plugins.push(plugin('upstream'));
  markets['self-hosted'] = { plugins: [plugin('ours')] };
  assert.equal(mergeMarkets(markets).market.plugins[0].source.repo, 'ours');
});

test('science entries are removed from all markets including fallback and alternates', () => {
  const markets = Object.fromEntries(SOURCE_ORDER.map(id => [id, { plugins: [] }]));
  const names = ['ambertools','chembl-database','gromacs','materials-project','ncbi-blast-biopython','openbabel','oqmd','pdb-database','pubchem-database','pubmed-pmc-paper-lookup','scientific-database-lookup','uniprot-database'];
  for (const name of names) markets.anthropic.plugins.push({ name, source: { repo: 'upstream' }, 'x-omnimind': {} });
  const merged = mergeMarkets(markets);
  assert.equal(merged.market.plugins.length, 0);
  assert.equal(markets.anthropic.plugins.length, 0);
  assert.equal(merged.duplicates.length, 0);
});
