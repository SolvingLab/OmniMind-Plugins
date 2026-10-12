import assert from 'node:assert/strict';
import { test } from 'node:test';
import { attachCatalogGithub, entriesRetainedAfterMetadataFailure } from './build.mjs';
import { GitHub, applyGithubDetails, decayKey, detailMetadataQuery, githubDetailFields, metadataFields, metadataQuery } from './lib/github.mjs';
import { loadCategories } from './lib/categories.mjs';
import { admissionProblems } from './readers/community.mjs';
import { validateMarketplace } from './validate-v2.mjs';

const SHA = 'a'.repeat(40);
const FETCHED_AT = '2026-10-12T00:00:00.000Z';

function source(path = 'plugins/demo') {
  return { source: 'github', repo: 'acme/plugin', path, sha: SHA };
}

function plugin(path = 'plugins/demo') {
  return {
    name: 'demo',
    source: source(path),
    category: 'coding',
    strict: true,
    'x-omnimind': { sourceId: 'community', manifestPath: 'plugins/demo/.claude-plugin/plugin.json' },
  };
}

function market(plugins) {
  return { name: 'omnimind-ext', plugins };
}

const metaFixture = {
  repo: 'acme/plugin',
  private: false,
  notFound: false,
  stars: 12,
  forks: 3,
  pushedAt: '2026-10-11T07:47:50Z',
  license: 'Apache-2.0',
  hasDiscussionsEnabled: true,
  homepageUrl: 'https://repo.example/docs',
  contributingUrl: 'https://github.com/acme/plugin/blob/main/CONTRIBUTING.md',
  branch: 'main',
  readmePath: 'README.md',
};

test('detail fields use the repository root and omit anything not fetched', () => {
  const fields = githubDetailFields(source('plugins/demo'), metaFixture, {
    fetchedAt: FETCHED_AT,
    homepage: 'https://plugin.example/docs',
  });
  assert.equal(fields.repository, 'https://github.com/acme/plugin');
  assert.equal(fields.repository.includes('plugins/demo'), false);
  assert.equal(fields.license, 'Apache-2.0');
  assert.equal(fields.updatedAt, '2026-10-11T07:47:50.000Z');
  assert.deepEqual(fields.github, { stars: 12, forks: 3, fetchedAt: FETCHED_AT });
  assert.equal(fields.links.docs, 'https://plugin.example/docs');
  assert.equal(fields.links.releases, 'https://github.com/acme/plugin/releases');
  assert.equal(fields.links.issues, 'https://github.com/acme/plugin/issues');
  assert.equal(fields.links.discussions, 'https://github.com/acme/plugin/discussions');
  assert.equal(fields.links.contributing, 'https://github.com/acme/plugin/blob/main/CONTRIBUTING.md');
  validateMarketplace(market([applyGithubDetails(plugin(), source(), metaFixture, {
    fetchedAt: FETCHED_AT,
    homepage: 'https://plugin.example/docs',
  })]));
});

test('failed or missing metadata does not invent zero stats', () => {
  for (const meta of [undefined, null, { detailUnavailable: true, stars: 0, forks: 0, license: 'MIT', pushedAt: '2026-01-01T00:00:00Z' }]) {
    const fields = githubDetailFields(source(), meta, { fetchedAt: FETCHED_AT, homepage: 'http://insecure.example' });
    assert.equal(fields.repository, 'https://github.com/acme/plugin');
    assert.equal(fields.github, undefined);
    assert.equal(fields.license, undefined);
    assert.equal(fields.updatedAt, undefined);
    assert.equal(fields.links.discussions, undefined);
    assert.equal(fields.links.contributing, undefined);
    assert.equal(fields.links.docs, undefined);
    assert.equal(JSON.stringify(fields).includes('"stars":0'), false);
    assert.equal(JSON.stringify(fields).includes('"forks":0'), false);
  }
});

test('docs falls back from https homepage to README and skips disabled extras', () => {
  const fields = githubDetailFields(source(), {
    ...metaFixture,
    hasDiscussionsEnabled: false,
    homepageUrl: 'http://repo.example',
    contributingUrl: 'http://github.com/acme/plugin/blob/main/CONTRIBUTING.md',
    license: 'NOASSERTION',
    forks: undefined,
    stars: 0,
  }, { fetchedAt: FETCHED_AT });
  assert.equal(fields.license, undefined);
  assert.equal(fields.links.docs, 'https://github.com/acme/plugin/blob/main/README.md');
  assert.equal(fields.links.discussions, undefined);
  assert.equal(fields.links.contributing, undefined);
  assert.deepEqual(fields.github, { stars: 0, fetchedAt: FETCHED_AT });
  assert.equal(Object.hasOwn(fields.github, 'forks'), false);
});

test('catalog attachment prefers an explicit https homepage and keeps extension metadata', () => {
  const record = {
    source: source(),
    entry: { homepage: 'https://docs.example/guide' },
    manifest: { homepage: 'https://manifest.example', interface: { websiteURL: 'https://ui.example' } },
    plugin: plugin(),
  };
  attachCatalogGithub([record], {
    detailFetchedAt: FETCHED_AT,
    meta: new Map([['acme/plugin', metaFixture]]),
  });
  assert.equal(record.plugin.links.docs, 'https://docs.example/guide');
  assert.equal(record.plugin['x-omnimind'].sourceId, 'community');
  assert.equal(Object.keys(record.plugin).at(-1), 'x-omnimind');
});

test('no client still emits repository links and does not throw or write zero', () => {
  const record = { source: source(), entry: {}, manifest: {}, plugin: plugin() };
  assert.doesNotThrow(() => attachCatalogGithub([record], undefined));
  assert.equal(record.plugin.repository, 'https://github.com/acme/plugin');
  assert.equal(record.plugin.github, undefined);
  assert.equal(record.plugin.links.issues, 'https://github.com/acme/plugin/issues');
  assert.equal(record.plugin.links.releases, 'https://github.com/acme/plugin/releases');
});

test('validator accepts absent details and real zero, rejects bad numbers and links', () => {
  validateMarketplace(market([plugin()]));
  validateMarketplace(market([applyGithubDetails(plugin(), source(), { ...metaFixture, stars: 0, forks: 0 }, { fetchedAt: FETCHED_AT })]));
  const bad = [
    { ...plugin(), repository: 'https://github.com/acme/plugin/plugins/demo' },
    { ...plugin(), license: 'NOASSERTION' },
    { ...plugin(), updatedAt: 'yesterday' },
    { ...plugin(), github: { stars: -1 } },
    { ...plugin(), github: { stars: 1.5 } },
    { ...plugin(), github: { forks: '0' } },
    { ...plugin(), github: {} },
    { ...plugin(), github: { stars: 1, watchers: 2 } },
    { ...plugin(), links: { docs: 'http://example.com' } },
    { ...plugin(), links: { docs: 'https://user:pass@example.com/docs' } },
    { ...plugin(), repository: 'https://github.com/acme/plugin', links: { issues: 'https://github.com/acme/plugin/issues/' } },
  ];
  for (const entry of bad) assert.throws(() => validateMarketplace(market([entry])), /repository|license|updatedAt|github|links/);
});

test('metadata query is batched once per repository and can drop detail fields', () => {
  assert.match(metadataFields(true), /forkCount/);
  assert.match(metadataFields(true), /hasDiscussionsEnabled/);
  assert.equal(metadataFields(false).includes('forkCount'), false);
  assert.equal(metadataFields(false).includes('licenseInfo'), true);
  const query = metadataQuery(['acme/plugin', 'other/repo'], true);
  assert.equal(query.includes('forkCount'), true);
  assert.equal([...query.matchAll(/repository\(owner:/g)].length, 2);
  const admission = metadataQuery(['acme/plugin'], false);
  const detail = detailMetadataQuery(['acme/plugin']);
  assert.equal(admission.includes('licenseInfo'), true);
  assert.equal(admission.includes('forkCount'), false);
  assert.equal(detail.includes('forkCount'), true);
  assert.equal(detail.includes('licenseInfo'), false);
  assert.equal(detail.includes('stargazerCount'), false);
  assert.throws(() => metadataQuery(['not a repo']), /Invalid GitHub repository/);
});

test('detail query failure falls back without writing zero forks', async () => {
  const calls = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (_url, init) => {
    const query = JSON.parse(init.body).query;
    calls.push(query);
    if (query.includes('forkCount')) {
      return new Response(JSON.stringify({ errors: [{ type: 'COMPLEXITY', message: 'max' }], data: null }), { status: 200 });
    }
    return new Response(JSON.stringify({ data: { r0: {
      nameWithOwner: 'acme/plugin', isPrivate: false, isArchived: false, isFork: false,
      stargazerCount: 0, createdAt: '2020-01-01T00:00:00Z', pushedAt: '2026-01-02T03:04:05Z',
      description: null, licenseInfo: { spdxId: 'MIT' }, repositoryTopics: { nodes: [] },
      defaultBranchRef: { name: 'main', target: { oid: SHA } },
    } } }), { status: 200 });
  };
  try {
    const client = new GitHub({ token: 'test-token' });
    client.detailRetryMs = 0;
    await client.metadataBatch(['acme/plugin', 'Acme/Plugin']);
    assert.equal(calls.length, 4);
    assert.equal(client.stats.detailFallbacks, 1);
    const meta = client.meta.get('acme/plugin');
    assert.equal(meta.stars, 0);
    assert.equal(Object.hasOwn(meta, 'forks'), false);
    const fields = githubDetailFields(source(), meta, { fetchedAt: client.detailFetchedAt });
    assert.equal(fields.github.stars, 0);
    assert.equal(Object.hasOwn(fields.github, 'forks'), false);
    assert.equal(fields.license, 'MIT');
  } finally {
    globalThis.fetch = original;
  }
});

test('metadata failure omits detail fields and does not fail the build', async () => {
  const original = globalThis.fetch;
  const originalWarn = console.warn;
  const warnings = [];
  console.warn = (...args) => warnings.push(args.join(' '));
  globalThis.fetch = async () => new Response('no', { status: 400 });
  try {
    const client = new GitHub({ token: 'test-token' });
    client.detailRetryMs = 0;
    await client.metadataBatch(['acme/plugin']);
    assert.equal(client.meta.get('acme/plugin').metadataUnavailable, true);
    const fields = githubDetailFields(source(), client.meta.get('acme/plugin'), { fetchedAt: FETCHED_AT });
    assert.equal(fields.github, undefined);
    assert.equal(fields.license, undefined);
    assert.equal(JSON.stringify(fields).includes(':0'), false);
    const record = { source: source(), entry: {}, manifest: {}, plugin: plugin() };
    assert.doesNotThrow(() => attachCatalogGithub([record], client));
    assert.equal(record.plugin.github, undefined);
    assert.equal(record.plugin.license, undefined);

    const bare = new GitHub({ token: '' });
    assert.equal(bare.token, undefined);
    const noToken = { source: source(), entry: {}, manifest: {}, plugin: plugin() };
    assert.doesNotThrow(() => attachCatalogGithub([noToken], bare));
    assert.equal(noToken.plugin.github, undefined);
    assert.equal(warnings.some(warning => /optional GitHub detail metadata omitted \(no token\)/.test(warning)), true);
    assert.equal(warnings.some(warning => /metadata_unavailable: acme\/plugin/.test(warning)), true);
  } finally {
    console.warn = originalWarn;
    globalThis.fetch = original;
  }
});

test('a transient detail failure is retried before fields are omitted', async () => {
  const original = globalThis.fetch;
  let detailed = 0;
  globalThis.fetch = async (_url, init) => {
    const query = JSON.parse(init.body).query;
    if (!query.includes('forkCount')) {
      return new Response(JSON.stringify({ data: { r0: {
        nameWithOwner: 'acme/plugin', isPrivate: false, isArchived: false, isFork: false,
        stargazerCount: 2, createdAt: '2020-01-01T00:00:00Z', pushedAt: '2026-02-03T04:05:06Z',
        description: null, licenseInfo: { spdxId: 'MIT' }, repositoryTopics: { nodes: [] },
        defaultBranchRef: { name: 'main', target: { oid: SHA } },
      } } }), { status: 200 });
    }
    detailed++;
    if (detailed === 1) return new Response(JSON.stringify({ errors: [{ type: 'RATE_LIMITED', message: 'slow down' }] }), { status: 200 });
    return new Response(JSON.stringify({ data: { r0: {
      nameWithOwner: 'acme/plugin', isPrivate: false, isArchived: false, isFork: false,
      stargazerCount: 2, forkCount: 5, hasDiscussionsEnabled: true,
      createdAt: '2020-01-01T00:00:00Z', pushedAt: '2026-02-03T04:05:06Z',
      description: null, licenseInfo: { spdxId: 'MIT' }, repositoryTopics: { nodes: [] },
      contributingGuidelines: null, homepageUrl: null,
      defaultBranchRef: { name: 'main', target: { oid: SHA } },
    } } }), { status: 200 });
  };
  try {
    const client = new GitHub({ token: 'test-token' });
    client.detailRetryMs = 0;
    await client.metadataBatch(['acme/plugin']);
    assert.equal(detailed, 2);
    assert.equal(client.stats.detailFallbacks, 0);
    const fields = githubDetailFields(source(), client.meta.get('acme/plugin'), { fetchedAt: client.detailFetchedAt });
    assert.equal(fields.github.forks, 5);
    assert.equal(fields.links.discussions, 'https://github.com/acme/plugin/discussions');
  } finally {
    globalThis.fetch = original;
  }
});

test('partial detail errors keep returned counts and omit missing forks', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({
    errors: [{ type: 'FIELD_ERROR', message: 'forkCount unavailable' }],
    data: { r0: {
      nameWithOwner: 'acme/plugin', isPrivate: false, isArchived: false, isFork: false,
      stargazerCount: 8, forkCount: null, hasDiscussionsEnabled: null,
      createdAt: '2020-01-01T00:00:00Z', pushedAt: '2026-02-03T04:05:06Z',
      description: null, licenseInfo: { spdxId: 'MIT' }, repositoryTopics: { nodes: [] },
      contributingGuidelines: null, homepageUrl: null,
      defaultBranchRef: { name: 'main', target: { oid: SHA } },
    } },
  }), { status: 200 });
  try {
    const client = new GitHub({ token: 'test-token' });
    await client.metadataBatch(['acme/plugin']);
    assert.equal(client.stats.detailFallbacks, 0);
    assert.equal(client.stats.detailPartial, 1);
    const fields = githubDetailFields(source(), client.meta.get('acme/plugin'), { fetchedAt: client.detailFetchedAt });
    assert.equal(fields.github.stars, 8);
    assert.equal(Object.hasOwn(fields.github, 'forks'), false);
    assert.equal(fields.links.discussions, undefined);
  } finally {
    globalThis.fetch = original;
  }
});

test('successful detail batch maps forks, discussions, and contributing without a second repo query', async () => {
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return new Response(JSON.stringify({ data: { r0: {
      nameWithOwner: 'acme/plugin', isPrivate: false, isArchived: false, isFork: false,
      stargazerCount: 4, forkCount: 0, hasDiscussionsEnabled: false, homepageUrl: null,
      createdAt: '2020-01-01T00:00:00Z', pushedAt: '2026-02-03T04:05:06Z',
      description: null, licenseInfo: null, repositoryTopics: { nodes: [] },
      contributingGuidelines: { url: 'https://github.com/acme/plugin/blob/main/.github/CONTRIBUTING.md' },
      defaultBranchRef: { name: 'main', target: { oid: SHA } },
      readmeMd: { oid: 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb' },
    } } }), { status: 200 });
  };
  try {
    const client = new GitHub({ token: 'test-token' });
    await client.metadataBatch(['acme/plugin', 'acme/plugin']);
    assert.equal(calls, 2);
    const meta = client.meta.get('acme/plugin');
    assert.equal(meta.forks, 0);
    assert.equal(meta.hasDiscussionsEnabled, false);
    assert.equal(meta.readmePath, 'README.md');
    const fields = githubDetailFields(source('plugins/nested'), meta, { fetchedAt: client.detailFetchedAt });
    assert.equal(fields.repository, 'https://github.com/acme/plugin');
    assert.equal(fields.github.forks, 0);
    assert.equal(fields.links.docs, 'https://github.com/acme/plugin/blob/main/README.md');
    assert.equal(fields.links.contributing, 'https://github.com/acme/plugin/blob/main/.github/CONTRIBUTING.md');
    assert.equal(fields.links.discussions, undefined);
    validateMarketplace(market([applyGithubDetails(plugin('plugins/nested'), source('plugins/nested'), meta, { fetchedAt: client.detailFetchedAt })]));
  } finally {
    globalThis.fetch = original;
  }
});

test('licenseInfo detail error does not exclude or become missing_license', async () => {
  const original = globalThis.fetch;
  const now = new Date('2026-10-12T00:00:00Z');
  globalThis.fetch = async (_url, init) => {
    const query = JSON.parse(init.body).query;
    if (query.includes('forkCount')) {
      return new Response(JSON.stringify({
        errors: [{ type: 'INTERNAL', path: ['r0', 'licenseInfo'], message: 'temporary field error' }],
        data: { r0: { forkCount: 15, licenseInfo: null, hasDiscussionsEnabled: true } },
      }), { status: 200 });
    }
    return new Response(JSON.stringify({ data: { r0: {
      nameWithOwner: 'acme/plugin', isPrivate: false, isArchived: false, isFork: false,
      stargazerCount: 800, createdAt: '2020-01-01T00:00:00Z', pushedAt: '2026-10-11T00:00:00Z',
      description: null, licenseInfo: { spdxId: 'MIT' },
      repositoryTopics: { nodes: [{ topic: { name: 'claude-code-plugin' } }] },
      defaultBranchRef: { name: 'main', target: { oid: SHA } },
    } } }), { status: 200 });
  };
  try {
    const client = new GitHub({ token: 'test-token' });
    await client.metadataBatch(['acme/plugin']);
    const meta = client.meta.get('acme/plugin');
    assert.equal(meta.metadataUnavailable, undefined);
    assert.equal(meta.license, 'MIT');
    assert.equal(meta.forks, 15);
    assert.deepEqual(admissionProblems(meta, { now, existing: true }), []);
  } finally {
    globalThis.fetch = original;
  }
});

test('admission licenseInfo field error is metadata_unavailable and keeps a previous entry', async () => {
  const client = new GitHub({ token: 'test-token' });
  client.detailRetryMs = 0;
  client.graphqlPartial = async () => ({
    errors: [{ type: 'INTERNAL', path: ['r0', 'licenseInfo'], message: 'temporary field error' }],
    data: { r0: {
      nameWithOwner: 'acme/plugin', isPrivate: false, isArchived: false, isFork: false,
      stargazerCount: 800, forkCount: 15, createdAt: '2020-01-01T00:00:00Z',
      pushedAt: '2026-10-11T00:00:00Z', licenseInfo: null,
      repositoryTopics: { nodes: [{ topic: { name: 'claude-code-plugin' } }] },
      defaultBranchRef: { name: 'main', target: { oid: SHA } },
    } },
  });
  await client.metadataBatch(['acme/plugin']);
  const meta = client.meta.get('acme/plugin');
  const problems = admissionProblems(meta, { now: new Date('2026-10-12T00:00:00Z'), existing: true });
  assert.equal(problems.includes('missing_license'), false);
  assert.deepEqual(problems, ['metadata_unavailable']);
  const previous = [applyGithubDetails(plugin(), source(), metaFixture, { fetchedAt: FETCHED_AT })];
  const { kept, skipped } = entriesRetainedAfterMetadataFailure(previous, [meta.repo]);
  assert.equal(kept.length, 1);
  assert.equal(kept[0].name, 'demo');
  assert.equal(kept[0].source.repo, 'acme/plugin');
  assert.deepEqual(skipped, []);
  const fields = githubDetailFields(source(), meta, { fetchedAt: FETCHED_AT });
  assert.equal(fields.github, undefined);
  assert.equal(JSON.stringify(fields).includes(':0'), false);
});

function catalogPlugin(name, repo) {
  return {
    name,
    category: 'coding',
    strict: true,
    source: { source: 'github', repo, path: '', sha: SHA },
    'x-omnimind': { sourceId: 'anthropic', manifestPath: '.claude-plugin/plugin.json' },
  };
}

test('catalog fallback rechecks repository status and decay before reusing previous entries', async () => {
  const { retainPreviousEntries, selectCatalogFallbackPlugins } = await import('./build.mjs');
  assert.equal(typeof selectCatalogFallbackPlugins, 'function');
  assert.equal(typeof retainPreviousEntries, 'function');
  const archived = catalogPlugin('archived-plugin', 'acme/archived');
  const missing = catalogPlugin('missing-plugin', 'acme/missing');
  const removed = catalogPlugin('removed-plugin', 'acme/removed');
  const removedUnqueryable = catalogPlugin('removed-unqueryable', 'acme/removed-unqueryable');
  const unqueryable = catalogPlugin('unqueryable-plugin', 'acme/unqueryable');
  const healthy = catalogPlugin('healthy-plugin', 'acme/healthy');
  const now = new Date('2026-10-12T00:00:00Z');
  const decayEntries = {
    [decayKey(removed.source)]: { status: 'removed', reasons: ['unsupported_manifest'], subjects: [] },
    [decayKey(removedUnqueryable.source)]: { status: 'removed', reasons: ['not_found'], subjects: [] },
  };
  const metaByRepo = new Map([
    ['acme/archived', { repo: 'acme/archived', private: false, archived: true, sha: SHA }],
    ['acme/missing', { repo: 'acme/missing', notFound: true }],
    ['acme/removed', { repo: 'acme/removed', private: false, archived: false, sha: SHA, stars: 20, pushedAt: '2026-10-01T00:00:00Z' }],
    ['acme/removed-unqueryable', { repo: 'acme/removed-unqueryable', metadataUnavailable: true }],
    ['acme/unqueryable', { repo: 'acme/unqueryable', metadataUnavailable: true }],
    ['acme/healthy', { repo: 'acme/healthy', private: false, archived: false, sha: SHA, stars: 20, pushedAt: '2026-10-01T00:00:00Z' }],
  ]);
  const selected = selectCatalogFallbackPlugins([archived, missing, removed, removedUnqueryable, unqueryable, healthy], {
    metaByRepo, decayEntries, sourceId: 'anthropic', now,
  });
  assert.deepEqual(selected.kept.map(plugin => plugin.name), ['unqueryable-plugin', 'healthy-plugin']);
  assert.deepEqual(selected.dropped.map(item => item.plugin.name), ['archived-plugin', 'missing-plugin', 'removed-plugin', 'removed-unqueryable']);
  assert.equal(selected.dropped.find(item => item.plugin.name === 'archived-plugin').reason, 'archived');
  assert.equal(selected.dropped.find(item => item.plugin.name === 'missing-plugin').reason, 'not_found');
  assert.equal(selected.dropped.find(item => item.plugin.name === 'removed-plugin').status, 'removed');

  const queried = [];
  const client = {
    meta: metaByRepo,
    metadataBatch: async repos => { queried.push(...repos); },
  };
  const fallback = await retainPreviousEntries(client, new Map([['anthropic', 'anthropics/claude-plugins-official']]), {
    state: { entries: decayEntries },
    now,
    mapping: await loadCategories(),
    readPrevious: async id => id === 'anthropic'
      ? { plugins: [archived, missing, removed, unqueryable, healthy] }
      : { plugins: [] },
  });
  assert.deepEqual(queried.sort(), ['acme/archived', 'acme/healthy', 'acme/missing', 'acme/removed', 'acme/unqueryable']);
  assert.deepEqual(fallback.records.map(record => record.plugin.name), ['unqueryable-plugin', 'healthy-plugin']);
  assert.equal(fallback.dropped.length, 3);
  assert.equal(fallback.reused.has('acme/archived'), false);
  assert.equal(fallback.reused.has('acme/unqueryable'), true);
});

test('fallback entries use the same selected recording path as fresh entries', async () => {
  const { recordAcceptedEntry, SOURCE_ORDER } = await import('./build.mjs');
  assert.equal(typeof recordAcceptedEntry, 'function');
  const selected = [];
  const seen = new Map(SOURCE_ORDER.map(id => [id, new Set()]));
  const freshSource = source();
  const fresh = {
    id: 'anthropic',
    plugin: { ...plugin(), name: 'fresh-plugin', source: freshSource },
    source: freshSource,
    classification: { category: 'coding', method: 'upstream', inputCategory: 'development', matches: [] },
  };
  assert.equal(recordAcceptedEntry(selected, seen, fresh), true);
  const fallbackPlugin = catalogPlugin('reused-plugin', 'acme/reused');
  fallbackPlugin.category = 'office';
  const mapping = await loadCategories();
  const { classifyCategory } = await import('./lib/categories.mjs');
  const fallback = {
    id: 'anthropic',
    plugin: fallbackPlugin,
    source: fallbackPlugin.source,
    classification: classifyCategory(fallbackPlugin.category, mapping),
  };
  assert.equal(recordAcceptedEntry(selected, seen, fallback), true);
  assert.equal(recordAcceptedEntry(selected, seen, fallback), false);
  const assignments = selected.map(record => ({
    id: record.id,
    name: record.plugin.name,
    source: record.source,
    ...record.classification,
  }));
  assert.equal(selected.length, 2);
  assert.equal(assignments.length, selected.length);
  assert.equal(assignments.find(item => item.name === 'reused-plugin').category, 'office');
  assert.equal(assignments.find(item => item.name === 'reused-plugin').method, 'upstream');
});

test('partial detail errors warn once per repository without tokens or query URLs', async () => {
  const original = globalThis.fetch;
  const originalWarn = console.warn;
  const warnings = [];
  console.warn = (...args) => warnings.push(args.join(' '));
  const admission = repo => ({
    nameWithOwner: repo, isPrivate: false, isArchived: false, isFork: false,
    stargazerCount: 8, createdAt: '2020-01-01T00:00:00Z', pushedAt: '2026-02-03T04:05:06Z',
    description: null, licenseInfo: { spdxId: 'MIT' }, repositoryTopics: { nodes: [] },
    defaultBranchRef: { name: 'main', target: { oid: SHA } },
  });
  globalThis.fetch = async (_url, init) => {
    const query = JSON.parse(init.body).query;
    if (!query.includes('forkCount')) {
      return new Response(JSON.stringify({ data: { r0: admission('acme/plugin'), r1: admission('other/repo') } }), { status: 200 });
    }
    return new Response(JSON.stringify({
      errors: [
        { type: 'FIELD_ERROR', path: ['r0', 'forkCount'], message: 'https://api.github.com/graphql?access_token=ghp_supersecret' },
        { type: 'FIELD_ERROR', path: ['r1', 'hasDiscussionsEnabled'], message: 'Bearer ghp_supersecret' },
      ],
      data: {
        r0: { forkCount: null, hasDiscussionsEnabled: true, homepageUrl: null, contributingGuidelines: null },
        r1: { forkCount: 2, hasDiscussionsEnabled: null, homepageUrl: null, contributingGuidelines: null },
      },
    }), { status: 200 });
  };
  try {
    const client = new GitHub({ token: 'ghp_supersecret' });
    await client.metadataBatch(['acme/plugin', 'other/repo']);
    assert.equal(client.stats.detailPartial, 1);
    const partial = (client.detailWarnings ?? warnings).filter(warning => warning.includes('optional GitHub detail metadata partial'));
    assert.equal(partial.length, 2);
    assert.equal(partial.some(warning => warning.includes('acme/plugin') && warning.includes('forkCount')), true);
    assert.equal(partial.some(warning => warning.includes('other/repo') && warning.includes('hasDiscussionsEnabled')), true);
    for (const warning of [...partial, ...warnings]) {
      assert.equal(warning.includes('ghp_supersecret'), false);
      assert.equal(warning.includes('access_token'), false);
      assert.equal(warning.includes('?'), false);
      assert.equal(/https?:\/\//i.test(warning), false);
    }
    const { mergeReportWarnings } = await import('./build.mjs');
    const merged = mergeReportWarnings(['Featured plugin not found in built catalogs: demo@omnimind-ext-anthropic'], client);
    assert.equal(merged.filter(warning => warning.includes('optional GitHub detail metadata partial')).length, 2);
  } finally {
    console.warn = originalWarn;
    globalThis.fetch = original;
  }
});
