import { readFile, readdir } from 'node:fs/promises';
import { basename, dirname, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { NAME_PATTERN, REPO_PATTERN, SHA_PATTERN, normalizePath, repositoryUrl, spdxLicense, isIsoTimestamp, nonNegativeInteger, httpsUrl } from './lib/github.mjs';
import { CATEGORIES } from './lib/categories.mjs';

export function validateMarketplace(value, label = 'marketplace') {
  const errors = [];
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${label}: expected an object`);
  if (typeof value.name !== 'string' || !NAME_PATTERN.test(value.name)) errors.push('invalid marketplace name');
  if (!Array.isArray(value.plugins)) errors.push('plugins must be an array');
  const seen = new Set();
  for (const [index, entry] of (Array.isArray(value.plugins) ? value.plugins : []).entries()) {
    const tag = `plugins[${index}]`;
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) { errors.push(`${tag}: expected an object`); continue; }
    if (typeof entry.name !== 'string' || !NAME_PATTERN.test(entry.name)) errors.push(`${tag}: invalid plugin name`);
    if (seen.has(entry.name)) errors.push(`${tag}: duplicate name ${entry.name}`);
    seen.add(entry.name);
    const source = entry.source;
    if (!source || typeof source !== 'object' || Array.isArray(source) || source.source !== 'github') errors.push(`${tag}: source must be github`);
    else {
      if (typeof source.repo !== 'string' || !REPO_PATTERN.test(source.repo)) errors.push(`${tag}: invalid repo`);
      if (typeof source.sha !== 'string' || !SHA_PATTERN.test(source.sha)) errors.push(`${tag}: sha must be 40 hex characters`);
      if (typeof source.path !== 'string') errors.push(`${tag}: path must be a string`);
      else {
        try { if (normalizePath(source.path) !== source.path) errors.push(`${tag}: path must be normalized`); }
        catch { errors.push(`${tag}: unsafe source path`); }
      }
      const extra = Object.keys(source).filter(k => !['source', 'repo', 'path', 'sha'].includes(k));
      if (extra.length) errors.push(`${tag}: unexpected source fields ${extra.join(', ')}`);
    }
    if (entry.icon !== undefined) {
      try {
        if (typeof entry.icon !== 'string') throw new Error();
        const u = new URL(entry.icon);
        if (u.protocol !== 'https:' || u.username || u.password) throw new Error();
      } catch { errors.push(`${tag}: icon must be an https URL`); }
    }
    if (!CATEGORIES.includes(entry.category)) errors.push(`${tag}: category must be one of the seven categories`);
    validateGithubDetails(entry, tag, errors);
    for (const alternate of entry['x-omnimind']?.alternates ?? []) {
      if (alternate.name !== entry.name || !NAME_PATTERN.test(alternate.marketplace)) errors.push(`${tag}: invalid alternate identity`);
      if (alternate.source?.source !== 'github' || !SHA_PATTERN.test(alternate.source?.sha ?? '')) errors.push(`${tag}: invalid alternate pin`);
    }
  }
  if (errors.length) throw new Error(`${label}:\n${errors.join('\n')}`);
  return { name: value.name, plugins: value.plugins.length };
}

const GITHUB_KEYS = ['stars', 'forks', 'fetchedAt'];
const LINK_KEYS = ['docs', 'releases', 'issues', 'discussions', 'contributing'];
const LINK_SUFFIX = { issues: '/issues', releases: '/releases', discussions: '/discussions' };

function canonicalRepository(value) {
  if (typeof value !== 'string' || !value.startsWith('https://github.com/')) return undefined;
  const repo = value.slice('https://github.com/'.length);
  return repositoryUrl(repo) === value ? value : undefined;
}

function validateGithubDetails(entry, tag, errors) {
  const repository = entry.repository === undefined ? undefined : canonicalRepository(entry.repository);
  if (entry.repository !== undefined && !repository) errors.push(`${tag}: repository must be https://github.com/<owner>/<repo>`);
  if (entry.license !== undefined && spdxLicense(entry.license) !== entry.license) errors.push(`${tag}: license must be an SPDX id`);
  if (entry.updatedAt !== undefined && !isIsoTimestamp(entry.updatedAt)) errors.push(`${tag}: updatedAt must be an ISO-8601 timestamp`);
  if (entry.github !== undefined) {
    if (!entry.github || typeof entry.github !== 'object' || Array.isArray(entry.github)) errors.push(`${tag}: github must be an object`);
    else {
      const extra = Object.keys(entry.github).filter(key => !GITHUB_KEYS.includes(key));
      if (extra.length) errors.push(`${tag}: unexpected github fields ${extra.join(', ')}`);
      if (!Object.keys(entry.github).length) errors.push(`${tag}: github must not be empty`);
      for (const key of ['stars', 'forks']) {
        if (entry.github[key] !== undefined && nonNegativeInteger(entry.github[key]) === undefined) errors.push(`${tag}: github.${key} must be a non-negative integer`);
      }
      if (entry.github.fetchedAt !== undefined && !isIsoTimestamp(entry.github.fetchedAt)) errors.push(`${tag}: github.fetchedAt must be an ISO-8601 timestamp`);
    }
  }
  if (entry.links !== undefined) {
    if (!entry.links || typeof entry.links !== 'object' || Array.isArray(entry.links)) errors.push(`${tag}: links must be an object`);
    else {
      const extra = Object.keys(entry.links).filter(key => !LINK_KEYS.includes(key));
      if (extra.length) errors.push(`${tag}: unexpected link fields ${extra.join(', ')}`);
      if (!Object.keys(entry.links).length) errors.push(`${tag}: links must not be empty`);
      for (const [key, value] of Object.entries(entry.links)) {
        if (!LINK_KEYS.includes(key)) continue;
        if (httpsUrl(value) === undefined) errors.push(`${tag}: links.${key} must be an https URL`);
        else if (repository && LINK_SUFFIX[key] && value !== `${repository}${LINK_SUFFIX[key]}`) errors.push(`${tag}: links.${key} must be <repository>${LINK_SUFFIX[key]}`);
      }
    }
  }
}

async function expandFiles(args) {
  const files = [];
  for (const arg of args) {
    if (!/[?*]/.test(arg)) { files.push(resolve(arg)); continue; }
    const dir = resolve(dirname(arg));
    const pattern = new RegExp(`^${basename(arg).replace(/[.+^${}()|[\]\\]/g, '\\$&').replaceAll('*', '.*').replaceAll('?', '.')}$`);
    const matching = (await readdir(dir)).filter(name => pattern.test(name)).sort();
    if (!matching.length) throw new Error(`No files match ${arg}`);
    files.push(...matching.map(file => resolve(dir, file)));
  }
  return [...new Set(files)];
}

export async function validateFiles(args) {
  if (!args.length) throw new Error('Usage: node scripts/validate-v2.mjs dist/plugins.json dist/marketplaces/*.json');
  const seen = new Set();
  for (const file of await expandFiles(args)) {
    const result = validateMarketplace(JSON.parse(await readFile(file, 'utf8')), file);
    if (seen.has(result.name)) throw new Error(`Duplicate marketplace identity: ${result.name}`);
    seen.add(result.name);
    console.log(`PASS ${result.name}: ${result.plugins} plugins (${file})`);
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  validateFiles(process.argv.slice(2)).catch(error => { console.error(error.message); process.exitCode = 1; });
}
