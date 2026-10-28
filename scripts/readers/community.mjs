import { readFile, readdir } from 'node:fs/promises';
import { basename, resolve } from 'node:path';
import * as yaml from 'js-yaml';
import { ROOT, TOPICS, DAY, REPO_PATTERN, SHA_PATTERN, normalizePath, mapLimit, readJson, decayKey } from '../lib/github.mjs';
import { CATEGORIES, CATEGORY_LABELS } from '../lib/categories.mjs';
import { manifestRoots } from './solvinglab.mjs';

const ALLOWED_FIELDS = ['repo', 'path', 'ref', 'sha', 'category', 'summary', 'displayName', 'homepage'];

export async function readSubmission(file) {
  const value = yaml.load(await readFile(file, 'utf8'));
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${file}: YAML must be an object`);
  const extra = Object.keys(value).filter(k => !ALLOWED_FIELDS.includes(k));
  if (extra.length) throw new Error(`${file}: unknown fields ${extra.join(', ')}`);
  if (!REPO_PATTERN.test(value.repo ?? '')) throw new Error(`${file}: repo must be owner/repo`);
  const expected = `${value.repo.replace('/', '__')}.yml`;
  if (basename(file).toLowerCase() !== expected.toLowerCase()) throw new Error(`${file}: expected filename ${expected}`);
  const category = CATEGORIES.includes(value.category) ? value.category : CATEGORIES.find(slug => CATEGORY_LABELS[slug] === value.category);
  if (!category) throw new Error(`${file}: category must be one of the seven categories`);
  value.category = category;
  if (typeof value.summary !== 'string' || !value.summary.trim()) throw new Error(`${file}: summary is required`);
  for (const key of ['ref', 'displayName']) if (value[key] !== undefined && (typeof value[key] !== 'string' || !value[key].trim())) throw new Error(`${file}: ${key} must be a non-empty string`);
  if (value.sha !== undefined && !SHA_PATTERN.test(value.sha)) throw new Error(`${file}: sha must be a 40-character commit`);
  if (value.homepage !== undefined) {
    let u;
    try { u = new URL(value.homepage); } catch { throw new Error(`${file}: invalid homepage`); }
    if (u.protocol !== 'https:' || u.username || u.password) throw new Error(`${file}: homepage must use https`);
  }
  return { ...value, path: normalizePath(value.path) };
}

export async function submissionFiles() {
  const dir = resolve(ROOT, 'data/plugins');
  try { return (await readdir(dir)).filter(f => f.endsWith('.yml')).sort().map(f => resolve(dir, f)); }
  catch (error) { if (error.code === 'ENOENT') return []; throw error; }
}

export function admissionProblems(meta, { now = new Date(), existing = false } = {}) {
  if (!meta || meta.metadataUnavailable) return ['metadata_unavailable'];
  if (meta.notFound) return ['not_found'];
  if (meta.private) return ['private_repository'];
  const problems = [];
  if (meta.archived) problems.push('archived');
  if (meta.fork) problems.push('fork');
  if (!meta.license) problems.push('missing_license');
  if (!meta.topics.some(t => TOPICS.includes(t))) problems.push('missing_topic');
  if (/^awesome(?:[-_.]|$)/i.test(meta.repo.split('/')[1]) || meta.topics.includes('awesome-list')) problems.push('awesome_list');
  if (!meta.sha) problems.push('empty_repository');
  if (!Number.isFinite(Date.parse(meta.createdAt)) || (now.getTime() - Date.parse(meta.createdAt)) / DAY < 30) problems.push('too_young');
  if (!existing) {
    if (meta.stars < 500) problems.push('below_admission_stars');
    if (!Number.isFinite(Date.parse(meta.pushedAt)) || (now.getTime() - Date.parse(meta.pushedAt)) / DAY > 180) problems.push('stale_at_admission');
  }
  return problems;
}

export async function inspectCommunityRepo(client, repo, options = {}) {
  const meta = await client.repository(repo);
  const problems = admissionProblems(meta, options);
  if (problems.length) return { meta, roots: [], problems };
  const roots = manifestRoots(await client.tree(meta.repo, meta.sha));
  if (roots.length > 20) problems.push('aggregator_over_20');
  if (!roots.length) problems.push('unsupported_manifest');
  return { meta, roots, problems };
}

export default async function community(client, { now = new Date(), state = { entries: {} } } = {}) {
  const searches = [];
  // Search's separate rate limit is lower than GraphQL's; serialize topics.
  for (const topic of TOPICS) searches.push(await client.searchTopic(topic, now));
  const files = await submissionFiles();
  const submissions = await Promise.all(files.map(async file => ({ file, value: await readSubmission(file) })));
  const previous = await readJson(resolve(ROOT, 'dist/marketplaces/community.json'), { plugins: [] });
  const existingSources = [...previous.plugins.map(p => p.source), ...Object.values(state.entries).flatMap(e => (e.subjects ?? []).filter(s => s.id === 'community').map(s => s.entry.source))];
  const existingRepos = new Set(existingSources.map(s => s.repo.toLowerCase()));
  const repos = [...new Set([...searches.flatMap(s => s.repos), ...submissions.map(s => s.value.repo), ...existingSources.map(s => s.repo)])].filter(repo => repo.toLowerCase() !== 'solvinglab/omnimind-plugins').sort();
  await client.metadataBatch(repos);
  const inspections = await mapLimit(repos, 4, async repo => ({ repo, ...await inspectCommunityRepo(client, repo, { now, existing: existingRepos.has(repo.toLowerCase()) }) }));
  const candidates = [];
  const rejections = [];
  for (const item of inspections) {
    if (item.problems.length) {
      rejections.push({ id: 'community', scope: 'repository', repo: item.repo, reason: item.problems[0], details: item.problems });
      continue;
    }
    const curated = submissions.filter(s => s.value.repo.toLowerCase() === item.repo.toLowerCase());
    for (const s of curated) {
      const { value: v } = s;
      candidates.push({ id: 'community', entry: { source: { source: 'github', repo: v.repo, path: v.path, sha: v.sha, ref: v.ref }, category: v.category, description: v.summary, description_i18n: { 'zh-CN': v.summary }, displayName: v.displayName, homepage: v.homepage }, submission: basename(s.file) });
    }
    const curatedPaths = new Set(curated.map(s => s.value.path));
    for (const path of item.roots.filter(p => !curatedPaths.has(p))) candidates.push({ id: 'community', entry: { source: { source: 'github', repo: item.meta.repo, path, sha: item.meta.sha } } });
    // Keep formerly listed paths for disappearance/decay accounting.
    const seen = new Set(candidates.filter(c => c.entry.source.repo.toLowerCase() === item.repo.toLowerCase()).map(c => decayKey(c.entry.source)));
    for (const source of existingSources.filter(s => s.repo.toLowerCase() === item.repo.toLowerCase() && !seen.has(decayKey(s)))) {
      candidates.push({ id: 'community', entry: { source: { ...source, sha: item.meta.sha } } });
    }
  }
  return { id: 'community', inspected: repos.length, searches: searches.map(s => ({ topic: s.topic, repositories: s.repos.length })), submissions: files.map(file => basename(file)), candidates, rejections };
}
