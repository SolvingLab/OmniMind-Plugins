import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cp, mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

test('build writes synthetic self-hosted package into dist', async () => {
  const root = await mkdtemp(resolve('.self-host-test-'));
  const sha = 'a'.repeat(40), repo = 'SolvingLab/OmniMind-Plugins';
  const oldFetch = globalThis.fetch;
  try {
    await cp('scripts', resolve(root, 'scripts'), { recursive: true });
    await cp('data', resolve(root, 'data'), { recursive: true });
    if (process.env.BASELINE_BUILD_FILE) await cp(process.env.BASELINE_BUILD_FILE, resolve(root, 'scripts/build.mjs'));
    await rm(resolve(root, 'data/plugins'), { recursive: true, force: true });
    await writeFile(resolve(root, 'data/decay-state.json'), JSON.stringify({ version: 1, entries: {} }));
    await writeFile(resolve(root, 'data/self-hosted.json'), JSON.stringify({ items: [{ name: 'example', sha, description: 'Example' }] }));
    const fixture = resolve('scripts/fixtures/self-hosted');
    const meta = new Map();
    const client = {
      meta, stats: {},
      async metadataBatch(repos) { for (const r of repos) if (!meta.has(r.toLowerCase())) meta.set(r.toLowerCase(), { repo: r, sha, topics: [], stars: 1000, createdAt: '2020-01-01T00:00:00Z', pushedAt: '2026-10-28T00:00:00Z', license: 'MIT' }); },
      async repository(r) { await this.metadataBatch([r]); return meta.get(r.toLowerCase()); },
      async file(r, _sha, path) { if (r !== repo) return JSON.stringify({ plugins: [] }); try { return await readFile(resolve(fixture, path), 'utf8'); } catch (e) { if (e.code === 'ENOENT') return null; throw e; } },
      async pin(parts) { return { source: { source: 'github', repo: parts.repo, path: parts.path, sha: parts.sha ?? sha } }; },
      async manifests(sources) { return new Map(await Promise.all(sources.map(async s => [`${s.repo.toLowerCase()}#${s.path}@${s.sha}`, { manifest: JSON.parse(await readFile(resolve(fixture, s.path, '.omnimind-plugin/plugin.json'), 'utf8')), manifestPath: `${s.path}/.omnimind-plugin/plugin.json` }]))); },
      async searchTopic(topic) { return { topic, repos: [] }; }, async publicOrgRepos() { return []; }, async tree() { return []; },
    };
    globalThis.fetch = async () => ({ ok: false, status: 404, url: 'https://github.com/', headers: new Headers(), body: null });
    const { build } = await import(pathToFileURL(resolve(root, 'scripts/build.mjs')).href);
    await build({ client, now: new Date('2026-10-28T00:00:00Z') });
    const dist = JSON.parse(await readFile(resolve(root, 'dist/plugins.json'), 'utf8'));
    const plugin = dist.plugins.find(p => p.name === 'example');
    assert.deepEqual(plugin?.source, { source: 'github', repo, path: 'plugins/example', sha });
  } finally { globalThis.fetch = oldFetch; await rm(root, { recursive: true, force: true }); }
});
