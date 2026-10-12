import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { posix, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = fileURLToPath(new URL('../../', import.meta.url));
export const NAME_PATTERN = /^[a-z0-9][a-z0-9._-]{0,127}$/;
export const SHA_PATTERN = /^[0-9a-f]{40}$/i;
export const REPO_PATTERN = /^[A-Za-z0-9][A-Za-z0-9-]*\/[A-Za-z0-9_.-]+$/;
export const MANIFESTS = ['.omnimind-plugin/plugin.json', '.claude-plugin/plugin.json', '.codex-plugin/plugin.json', '.zcode-plugin/plugin.json'];
export const TOPICS = ['claude-code-plugin', 'codex-plugin', 'claude-plugin', 'zcode-plugin'];
export const DAY = 86_400_000;

export async function mapLimit(values, limit, fn) {
  const out = new Array(values.length);
  let next = 0;
  await Promise.all(Array.from({ length: Math.min(limit, values.length) }, async () => {
    while (next < values.length) {
      const i = next++;
      out[i] = await fn(values[i], i);
    }
  }));
  return out;
}

export function normalizePath(value = '') {
  if (typeof value !== 'string' || /[\\\0]/.test(value) || value.startsWith('/') || /^[A-Za-z]:/.test(value)) {
    throw new Error('Invalid repository-relative path');
  }
  const stripped = value.replace(/^(\.\/)+/, '').replace(/\/+$/, '');
  if (stripped.split('/').some(p => p === '..' || p === '.git')) throw new Error('Unsafe repository-relative path');
  return stripped === '.' ? '' : posix.normalize(stripped || '.').replace(/^\.$/, '');
}

export function parseGithubUrl(value) {
  if (typeof value !== 'string') return null;
  const ssh = value.match(/^git@github\.com:([^/]+\/[^/]+?)(?:\.git)?$/i);
  if (ssh) return { repo: ssh[1], path: '' };
  let url;
  try { url = new URL(value); } catch { return null; }
  if (url.hostname.toLowerCase() !== 'github.com' || !['https:', 'http:'].includes(url.protocol) || url.username || url.password) return null;
  const parts = url.pathname.split('/').filter(Boolean);
  if (parts.length < 2) return null;
  const repo = `${parts[0]}/${parts[1].replace(/\.git$/i, '')}`;
  if (!REPO_PATTERN.test(repo)) return null;
  if (parts.length === 2) return { repo, path: '', ...(url.hash ? { ref: decodeURIComponent(url.hash.slice(1)) } : {}) };
  if (parts[2] === 'tree' && parts[3]) return { repo, ref: decodeURIComponent(parts[3]), path: normalizePath(parts.slice(4).join('/')) };
  return null;
}

// Only these fields are consumed by V2's github source resolver.
export function sourceParts(value, upstream) {
  if (typeof value === 'string' || value?.source === 'local') {
    if (!upstream) throw new Error('Local source needs an upstream repository');
    if (typeof value === 'string' && /^[a-z][a-z0-9+.-]*:/i.test(value)) return null;
    if (value?.source === 'local' && typeof value.path !== 'string') throw new Error('local source requires path');
    return { repo: upstream.repo, path: normalizePath(typeof value === 'string' ? value : value.path), sha: upstream.sha };
  }
  if (!value || typeof value !== 'object') return null;
  if (value.source === 'github') {
    if (!REPO_PATTERN.test(value.repo ?? '')) throw new Error('Invalid GitHub repository');
    return { repo: value.repo, path: normalizePath(value.path), sha: value.sha, ref: value.ref };
  }
  if (!['url', 'git-subdir', 'git'].includes(value.source)) return null;
  const parsed = parseGithubUrl(value.url);
  if (!parsed) return null;
  if (value.source === 'git-subdir' && typeof value.path !== 'string') throw new Error('git-subdir requires path');
  return { ...parsed, path: normalizePath(value.path ?? parsed.path), sha: value.sha, ref: value.ref ?? parsed.ref };
}

export function sourceKey(source) { return `${source.repo.toLowerCase()}#${source.path ?? ''}@${source.sha}`; }
export function decayKey(source) { return `${source.repo.toLowerCase()}#${source.path ?? ''}`; }

const SPDX_SENTINELS = new Set(['NOASSERTION', 'NONE', 'UNLICENSED']);
const SPDX_PATTERN = /^[A-Za-z0-9][A-Za-z0-9.+-]*$/;
const ISO_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/;
export const README_PROBES = [
  ['readmeMd', 'README.md'],
  ['readmeRst', 'README.rst'],
  ['readmeTxt', 'README.txt'],
  ['readmePlain', 'README'],
  ['readmeLower', 'readme.md'],
];

export function nonNegativeInteger(value) {
  return Number.isInteger(value) && value >= 0 ? value : undefined;
}

export function isIsoTimestamp(value) {
  return typeof value === 'string' && ISO_PATTERN.test(value) && Number.isFinite(Date.parse(value));
}

export function toIsoTimestamp(value) {
  if (typeof value !== 'string' || !value.includes('T') || !Number.isFinite(Date.parse(value))) return undefined;
  const iso = new Date(value).toISOString();
  return isIsoTimestamp(iso) ? iso : undefined;
}

export function httpsUrl(value) {
  if (typeof value !== 'string' || !value.trim()) return undefined;
  let url;
  try { url = new URL(value.trim()); } catch { return undefined; }
  if (url.protocol !== 'https:' || url.username || url.password) return undefined;
  return url.href;
}

export function spdxLicense(value) {
  if (typeof value !== 'string') return undefined;
  const id = value.trim();
  if (!SPDX_PATTERN.test(id) || SPDX_SENTINELS.has(id.toUpperCase())) return undefined;
  return id;
}

export function repositoryUrl(repo) {
  return typeof repo === 'string' && REPO_PATTERN.test(repo) ? `https://github.com/${repo}` : undefined;
}

function blobUrl(repo, branch, path) {
  const root = repositoryUrl(repo);
  if (!root || typeof path !== 'string' || !path || path.split('/').some(part => !part || part === '.' || part === '..')) return undefined;
  const ref = typeof branch === 'string' && /^[A-Za-z0-9._-]+$/.test(branch) ? branch : 'HEAD';
  return `${root}/blob/${encodeURIComponent(ref)}/${path.split('/').map(encodeURIComponent).join('/')}`;
}

// Optional detail-page fields. Missing metadata omits keys; it never invents 0.
export function githubDetailFields(source, meta, { fetchedAt, homepage } = {}) {
  if (!source || typeof source.repo !== 'string') return {};
  const repo = meta && typeof meta.repo === 'string' && REPO_PATTERN.test(meta.repo) ? meta.repo : source.repo;
  const root = repositoryUrl(repo);
  if (!root) return {};
  const unavailable = !meta || meta.notFound || meta.private || meta.detailUnavailable === true;
  const out = { repository: root };
  const links = {};
  const docs = httpsUrl(homepage)
    || (!unavailable ? httpsUrl(meta.homepageUrl) : undefined)
    || (!unavailable ? blobUrl(repo, meta.branch, meta.readmePath) : undefined);
  if (docs) links.docs = docs;
  links.releases = `${root}/releases`;
  links.issues = `${root}/issues`;
  if (!unavailable && meta.hasDiscussionsEnabled === true) links.discussions = `${root}/discussions`;
  const contributing = !unavailable ? httpsUrl(meta.contributingUrl) : undefined;
  if (contributing) links.contributing = contributing;
  out.links = links;
  if (unavailable) return out;
  const license = spdxLicense(meta.license);
  if (license) out.license = license;
  const updatedAt = toIsoTimestamp(meta.pushedAt);
  if (updatedAt) out.updatedAt = updatedAt;
  const github = {};
  const stars = nonNegativeInteger(meta.stars);
  const forks = nonNegativeInteger(meta.forks);
  if (stars !== undefined) github.stars = stars;
  if (forks !== undefined) github.forks = forks;
  const fetched = toIsoTimestamp(fetchedAt);
  if (fetched && (github.stars !== undefined || github.forks !== undefined)) github.fetchedAt = fetched;
  if (Object.keys(github).length) out.github = github;
  return out;
}

export function applyGithubDetails(plugin, source, meta, options) {
  const fields = githubDetailFields(source, meta, options);
  if (!Object.keys(fields).length) return plugin;
  const ext = plugin['x-omnimind'];
  if (ext) delete plugin['x-omnimind'];
  Object.assign(plugin, fields);
  if (ext) plugin['x-omnimind'] = ext;
  return plugin;
}

export async function readJson(file, fallback) {
  try { return JSON.parse((await readFile(file, 'utf8')).replace(/^\uFEFF/, '')); }
  catch (error) { if (error.code === 'ENOENT' && fallback !== undefined) return fallback; throw error; }
}

export async function writeJson(file, value) {
  await mkdir(resolve(file, '..'), { recursive: true });
  await writeFile(file, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

export function metadataFields(detailed = true) {
  const base = 'nameWithOwner isPrivate isArchived isFork stargazerCount createdAt pushedAt description licenseInfo { spdxId } repositoryTopics(first:100) { nodes { topic { name } } } defaultBranchRef { name target { oid } }';
  if (!detailed) return base;
  const readme = README_PROBES.map(([alias, path]) => `${alias}: object(expression:${JSON.stringify(`HEAD:${path}`)}) { ... on Blob { oid } }`).join(' ');
  return `${base} forkCount hasDiscussionsEnabled homepageUrl contributingGuidelines { url } ${readme}`;
}

export function metadataQuery(repos, detailed = true) {
  const fields = metadataFields(detailed);
  return `query { ${repos.map((repo, i) => {
    if (!REPO_PATTERN.test(repo)) throw new Error(`Invalid GitHub repository: ${repo}`);
    const [owner, name] = repo.split('/');
    return `r${i}: repository(owner:${JSON.stringify(owner)},name:${JSON.stringify(name)}) { ${fields} }`;
  }).join('\n')} }`;
}

function readmePathFrom(node) {
  return README_PROBES.find(([alias]) => node[alias]?.oid)?.[1];
}

function metadata(node, { detailed = true } = {}) {
  const value = {
    repo: node.nameWithOwner, private: node.isPrivate, archived: node.isArchived, fork: node.isFork,
    stars: node.stargazerCount, createdAt: node.createdAt, pushedAt: node.pushedAt,
    license: node.licenseInfo?.spdxId ?? null, description: node.description,
    topics: node.repositoryTopics?.nodes.map(t => t.topic.name) ?? [],
    branch: node.defaultBranchRef?.name, sha: node.defaultBranchRef?.target?.oid,
  };
  if (!detailed) return value;
  const forks = nonNegativeInteger(node.forkCount);
  if (forks !== undefined) value.forks = forks;
  if (typeof node.hasDiscussionsEnabled === 'boolean') value.hasDiscussionsEnabled = node.hasDiscussionsEnabled;
  if (typeof node.homepageUrl === 'string') value.homepageUrl = node.homepageUrl;
  if (typeof node.contributingGuidelines?.url === 'string') value.contributingUrl = node.contributingGuidelines.url;
  const readmePath = readmePathFrom(node);
  if (readmePath) value.readmePath = readmePath;
  return value;
}

export class GitHub {
  constructor({ token = process.env.GITHUB_TOKEN, cacheDir = resolve(ROOT, '.cache/github') } = {}) {
    if (!token) throw new Error('GITHUB_TOKEN is required (process environment only)');
    this.headers = { Accept: 'application/vnd.github+json', Authorization: `Bearer ${token}`, 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'OmniMind-Plugins' };
    this.cacheDir = cacheDir;
    this.meta = new Map();
    this.pending = new Map();
    this.stats = { requests: 0, cacheHits: 0, graphqlBatches: 0, detailFallbacks: 0 };
  }

  async cache(key) {
    const filename = createHash('sha256').update(key).digest('hex');
    try { this.stats.cacheHits++; return await readJson(resolve(this.cacheDir, `${filename}.json`)); }
    catch (error) { this.stats.cacheHits--; if (error.code === 'ENOENT') return undefined; throw error; }
  }

  async save(key, value) {
    const filename = createHash('sha256').update(key).digest('hex');
    await writeJson(resolve(this.cacheDir, `${filename}.json`), value);
  }

  async request(path, { method = 'GET', body, allow404 = false } = {}) {
    const url = `https://api.github.com/${path}`;
    for (let attempt = 0; attempt < 4; attempt++) {
      let response;
      try {
        this.stats.requests++;
        response = await fetch(url, {
          method, headers: { ...this.headers, ...(body ? { 'Content-Type': 'application/json' } : {}) },
          ...(body ? { body: JSON.stringify(body) } : {}), signal: AbortSignal.timeout(30_000),
        });
      } catch {
        if (attempt === 3) throw new Error(`GitHub network failure: ${method} ${path}`);
      }
      if (response?.ok) return response.json();
      if (response?.status === 404 && allow404) return null;
      const retryable = !response || [403, 429].includes(response.status) || response.status >= 500;
      if (!retryable || attempt === 3) throw new Error(`GitHub HTTP ${response?.status ?? 'network failure'}: ${method} ${path}`);
      const wait = Math.min(30_000, Number(response?.headers.get('retry-after')) * 1000 || 2000 * 2 ** attempt);
      await new Promise(r => setTimeout(r, wait));
    }
  }

  async graphql(query) {
    const result = await this.graphqlPartial(query);
    const unexpected = result.errors?.filter(e => e.type !== 'NOT_FOUND');
    if (unexpected?.length) throw new Error(`GitHub GraphQL query failed (${unexpected.map(e => e.type ?? 'unknown').join(', ')})`);
    return result;
  }

  async graphqlPartial(query) {
    this.stats.graphqlBatches++;
    const result = await this.request('graphql', { method: 'POST', body: { query } });
    const unexpected = result.errors?.filter(e => e.type !== 'NOT_FOUND');
    if (!result.data) {
      const reason = unexpected?.length ? unexpected.map(e => e.type ?? 'unknown').join(', ') : 'no data';
      throw new Error(`GitHub GraphQL query failed (${reason})`);
    }
    return result;
  }

  async restMetadata(repo) {
    const m = await this.request(`repos/${repo}`, { allow404: true });
    if (!m) return { repo, notFound: true };
    if (m.private) return { repo: m.full_name, private: true };
    const c = m.default_branch ? await this.request(`repos/${m.full_name}/commits/${encodeURIComponent(m.default_branch)}`) : null;
    const value = { repo: m.full_name, private: false, archived: m.archived, fork: m.fork,
      stars: m.stargazers_count, createdAt: m.created_at, pushedAt: m.pushed_at, license: m.license?.spdx_id ?? null,
      description: m.description, topics: m.topics ?? [], branch: m.default_branch, sha: c?.sha };
    const forks = nonNegativeInteger(m.forks_count);
    if (forks !== undefined) value.forks = forks;
    if (typeof m.has_discussions === 'boolean') value.hasDiscussionsEnabled = m.has_discussions;
    if (typeof m.homepage === 'string') value.homepageUrl = m.homepage;
    return value;
  }

  async metadataBatch(repos) {
    const todo = [];
    const seen = new Set();
    for (const repo of repos) {
      const key = String(repo).toLowerCase();
      if (seen.has(key) || this.meta.has(key)) continue;
      seen.add(key);
      todo.push(repo);
    }
    for (let start = 0; start < todo.length; start += 50) {
      const chunk = todo.slice(start, start + 50);
      // Validate before either request so a bad name does not look like a detail-field failure.
      const detailedQuery = metadataQuery(chunk, true);
      let result;
      let detailed = true;
      for (let attempt = 0; attempt < 3 && !result; attempt++) {
        try {
          // Partial field errors keep the nodes that arrived. Missing forks/discussions
          // stay absent; they are not retried into a zero.
          result = await this.graphqlPartial(detailedQuery);
          if (result.errors?.some(error => error.type !== 'NOT_FOUND')) this.stats.detailPartial = (this.stats.detailPartial ?? 0) + 1;
        } catch {
          if (attempt < 2) await new Promise(resolve => setTimeout(resolve, (this.detailRetryMs ?? 2_000) * 2 ** attempt));
        }
      }
      if (!result) {
        // Detail fields are optional. A failed extended query must not fail the catalog
        // build or be recorded as zero stars/forks; retry the fields decay already requires.
        result = await this.graphql(metadataQuery(chunk, false));
        detailed = false;
        this.stats.detailFallbacks++;
      }
      this.detailFetchedAt ??= new Date().toISOString();
      for (let i = 0; i < chunk.length; i++) {
        const node = result.data[`r${i}`];
        // Confirm NOT_FOUND through REST, which follows renamed repositories.
        const value = node ? metadata(node, { detailed }) : await this.restMetadata(chunk[i]);
        this.meta.set(chunk[i].toLowerCase(), value);
        if (value.repo) this.meta.set(value.repo.toLowerCase(), value);
      }
    }
    return this.meta;
  }

  async repository(repo) {
    if (!this.meta.has(repo.toLowerCase())) {
      const key = `meta:${repo.toLowerCase()}`;
      if (!this.pending.has(key)) this.pending.set(key, this.metadataBatch([repo]));
      await this.pending.get(key);
    }
    return this.meta.get(repo.toLowerCase());
  }

  async pin(parts) {
    const meta = await this.repository(parts.repo);
    if (meta.notFound || meta.private || !meta.sha) return { source: null, meta };
    let sha = parts.sha;
    if (sha !== undefined && !SHA_PATTERN.test(sha)) throw new Error('Source sha must be 40 hexadecimal characters');
    if (!sha && parts.ref && parts.ref !== meta.branch) {
      const key = `ref:${meta.repo}:${parts.ref}`;
      if (!this.pending.has(key)) this.pending.set(key, this.request(`repos/${meta.repo}/commits/${encodeURIComponent(parts.ref)}`));
      sha = (await this.pending.get(key)).sha;
    }
    sha ??= meta.sha;
    if (!SHA_PATTERN.test(sha)) throw new Error(`Unable to pin GitHub source: ${parts.repo}`);
    return { source: { source: 'github', repo: meta.repo, path: normalizePath(parts.path), sha: sha.toLowerCase() }, meta };
  }

  async file(repo, sha, path) {
    const m = await this.repository(repo);
    if (m.private || m.notFound) return null;
    if (!SHA_PATTERN.test(sha)) throw new Error('File read must use a pinned sha');
    const key = `file:${m.repo}:${sha}:${normalizePath(path)}`;
    const cached = await this.cache(key);
    if (cached !== undefined) return cached;
    const value = await this.request(`repos/${m.repo}/contents/${normalizePath(path).split('/').map(encodeURIComponent).join('/')}?ref=${sha}`, { allow404: true });
    const text = value ? Buffer.from(value.content ?? '', 'base64').toString('utf8').replace(/^\uFEFF/, '') : null;
    if (value && (value.type !== 'file' || value.encoding !== 'base64')) throw new Error(`Unsupported file response: ${repo}/${path}`);
    await this.save(key, text);
    return text;
  }

  async tree(repo, sha) {
    if (!SHA_PATTERN.test(sha)) throw new Error('Tree read must use a pinned sha');
    const m = await this.repository(repo);
    if (m.private || m.notFound) return [];
    const key = `tree:${m.repo}:${sha}`;
    const cached = await this.cache(key);
    if (cached !== undefined) return cached;
    const result = await this.request(`repos/${m.repo}/git/trees/${sha}?recursive=1`, { allow404: true });
    // Empty repositories have no HEAD sha; a tree 404 at a known commit is
    // inconclusive and must not be mistaken for an empty manifest inventory.
    if (!result) throw new Error(`GitHub tree unavailable at pinned sha: ${m.repo}@${sha}`);
    if (result.truncated) throw new Error(`GitHub tree truncated; cannot establish manifest inventory: ${m.repo}`);
    const paths = result.tree.filter(t => t.type === 'blob').map(t => t.path);
    await this.save(key, paths);
    return paths;
  }

  async manifests(sources) {
    const unique = [...new Map(sources.map(s => [sourceKey(s), s])).values()];
    const out = new Map();
    const todo = [];
    for (const source of unique) {
      // Do not reuse cached rejections from before .zcode-plugin support.
      const cached = await this.cache(`manifest-v2:${sourceKey(source)}`);
      if (cached === undefined) todo.push(source); else out.set(sourceKey(source), cached);
    }
    for (let start = 0; start < todo.length; start += 25) {
      const chunk = todo.slice(start, start + 25);
      const paths = MANIFESTS;
      const query = `query { ${chunk.map((source, i) => {
        const [owner, name] = source.repo.split('/');
        return `r${i}: repository(owner:${JSON.stringify(owner)},name:${JSON.stringify(name)}) { isPrivate commit: object(expression:${JSON.stringify(source.sha)}) { oid } ${paths.map((p, j) => `m${j}: object(expression:${JSON.stringify(`${source.sha}:${posix.join(source.path, p)}`)}) { ... on Blob { text } }`).join(' ')} }`;
      }).join('\n')} }`;
      const result = await this.graphql(query);
      for (let i = 0; i < chunk.length; i++) {
        const node = result.data[`r${i}`];
        let value;
        if (!node) throw new Error(`Repository unavailable while reading manifest: ${chunk[i].repo}`);
        if (node.isPrivate) value = { error: 'private_repository' };
        else if (!node.commit) value = { error: 'invalid_source_pin', detail: 'commit does not exist in public source repository' };
        else {
          const idx = MANIFESTS.findIndex((_, j) => typeof node[`m${j}`]?.text === 'string');
          if (idx < 0) value = { error: 'unsupported_manifest', detail: 'no supported plugin.json' };
          else {
            try {
              const manifest = JSON.parse(node[`m${idx}`].text.replace(/^\uFEFF/, ''));
              value = manifest && typeof manifest === 'object' && !Array.isArray(manifest)
                ? { manifest, manifestPath: posix.join(chunk[i].path, MANIFESTS[idx]) }
                : { error: 'invalid_manifest', detail: 'plugin.json must be an object' };
            } catch { value = { error: 'invalid_manifest', detail: 'plugin.json is not valid JSON' }; }
          }
        }
        if (!node.isPrivate) await this.save(`manifest-v2:${sourceKey(chunk[i])}`, value);
        out.set(sourceKey(chunk[i]), value);
      }
    }
    return out;
  }

  async publicOrgRepos(org) {
    const repos = [];
    for (let page = 1; ; page++) {
      const items = await this.request(`orgs/${encodeURIComponent(org)}/repos?type=public&per_page=100&page=${page}`);
      repos.push(...items.filter(r => !r.private).map(r => r.full_name));
      if (items.length < 100) break;
    }
    return repos.sort();
  }

  async searchTopic(topic, now = new Date()) {
    const date = days => new Date(now.getTime() - days * DAY).toISOString().slice(0, 10);
    const query = `topic:${topic} stars:>=500 pushed:>=${date(180)} created:<=${date(30)} archived:false fork:false`;
    const items = [];
    for (let page = 1; ; page++) {
      const result = await this.request(`search/repositories?q=${encodeURIComponent(query)}&sort=stars&per_page=100&page=${page}`);
      if (result.incomplete_results || result.total_count > 1000) throw new Error(`Incomplete GitHub search for ${topic}; refusing a partial catalog`);
      items.push(...result.items.filter(r => !r.private).map(r => r.full_name));
      if (items.length >= result.total_count || result.items.length < 100) break;
      await new Promise(r => setTimeout(r, 2100));
    }
    return { topic, repos: items };
  }
}

export async function readMarketplace(client, { id, repo, path }) {
  const meta = await client.repository(repo);
  if (meta.notFound || meta.private || !meta.sha) throw new Error(`Public upstream unavailable: ${repo}`);
  const raw = await client.file(repo, meta.sha, path);
  if (raw === null) throw new Error(`Upstream marketplace missing: ${repo}/${path}`);
  const value = JSON.parse(raw);
  if (!Array.isArray(value.plugins)) throw new Error(`Upstream plugins must be an array: ${repo}`);
  const upstream = { repo: meta.repo, sha: meta.sha, path };
  return { id, upstream, candidates: value.plugins.map(entry => ({ id, entry, upstream })), inspected: value.plugins.length };
}
