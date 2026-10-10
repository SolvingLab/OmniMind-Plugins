import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import * as yaml from 'js-yaml';
import anthropic from './readers/anthropic.mjs';
import openai from './readers/openai.mjs';
import zcode from './readers/zcode.mjs';
import solvinglab from './readers/solvinglab.mjs';
import community from './readers/community.mjs';
import { GitHub, ROOT, NAME_PATTERN, sourceParts, sourceKey, writeJson, mapLimit } from './lib/github.mjs';
import { CATEGORIES, loadCategories, assertMapped, categoryOf } from './lib/categories.mjs';
import { attachLogos } from './lib/logo.mjs';
import { loadDecayState, evaluateDecay, STATE_FILE } from './scan-decay.mjs';
import { validateMarketplace } from './validate-v2.mjs';

export const SOURCE_ORDER = ['anthropic', 'openai', 'zcode', 'solvinglab', 'community'];
export const marketplaceName = id => `omnimind-ext-${id}`;

function nonEmpty(value) { return typeof value === 'string' && value.trim() ? value : undefined; }
function stringMap(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined;
  const pairs = Object.entries(value).filter(([, v]) => typeof v === 'string');
  return pairs.length ? Object.fromEntries(pairs) : undefined;
}

export function createListing(record, loaded, mapping) {
  const { entry, id, source } = record;
  const { manifest, manifestPath } = loaded;
  const ui = manifest.interface ?? {};
  const name = manifest.name;
  const plugin = { name, source, category: categoryOf(entry.category ?? manifest.category ?? ui.category, mapping), strict: true };
  const strings = {
    description: entry.description ?? manifest.description ?? ui.longDescription ?? ui.shortDescription,
    version: manifest.version ?? entry.version,
    displayName: entry.displayName ?? manifest.displayName ?? ui.displayName,
    homepage: entry.homepage ?? manifest.homepage ?? ui.websiteURL ?? `https://github.com/${source.repo}`,
    privacyPolicy: entry.privacyPolicy ?? ui.privacyPolicyURL,
    termsOfService: entry.termsOfService ?? ui.termsOfServiceURL,
  };
  for (const [key, value] of Object.entries(strings)) if (nonEmpty(value)) plugin[key] = value;
  const author = entry.author ?? manifest.author ?? ui.developerName;
  if (nonEmpty(author)) plugin.author = author;
  else if (author && typeof author === 'object' && (nonEmpty(author.name) || nonEmpty(author.url))) {
    plugin.author = { ...(nonEmpty(author.name) ? { name: author.name } : {}), ...(nonEmpty(author.url) ? { url: author.url } : {}) };
  }
  for (const key of ['displayName_i18n', 'description_i18n']) {
    const value = stringMap(entry[key] ?? manifest[key]);
    if (value) plugin[key] = value;
  }
  const tags = entry.tags ?? entry.keywords ?? manifest.keywords;
  if (Array.isArray(tags)) plugin.tags = tags.filter(t => typeof t === 'string');
  if (Array.isArray(entry.examplePrompts ?? ui.defaultPrompt)) plugin.examplePrompts = (entry.examplePrompts ?? ui.defaultPrompt).filter(p => typeof p === 'string');
  // Retain qualified dependency references; normalization is the same as V2.
  if (Array.isArray(entry.dependencies)) plugin.dependencies = entry.dependencies.flatMap(d => {
    if (typeof d === 'string') return [d.replace(/@\^[^@]*$/u, '')];
    if (d && nonEmpty(d.name)) return [d.marketplace ? `${d.name}@${d.marketplace}` : d.name];
    return [];
  });
  plugin['x-omnimind'] = { sourceId: id, manifestPath,
    ...(entry.name && entry.name !== name ? { upstreamName: entry.name } : {}),
    ...(record.submission ? { submission: record.submission } : {}) };
  return { ...record, ...loaded, plugin };
}

export function mergeMarkets(markets) {
  const kept = new Map();
  const duplicates = new Map();
  for (const id of SOURCE_ORDER) {
    for (const plugin of markets[id].plugins) {
      if (!kept.has(plugin.name)) kept.set(plugin.name, { id, plugin: structuredClone(plugin) });
      else {
        const winner = kept.get(plugin.name);
        const alternate = { name: plugin.name, marketplace: marketplaceName(id), source: plugin.source };
        (winner.plugin['x-omnimind'].alternates ??= []).push(alternate);
        if (!duplicates.has(plugin.name)) duplicates.set(plugin.name, { name: plugin.name, winner: marketplaceName(winner.id), keptSource: winner.plugin.source, alternates: [] });
        duplicates.get(plugin.name).alternates.push(alternate);
      }
    }
  }
  return {
    market: { name: 'omnimind-ext', description: 'OmniMind 公开插件合并目录；同名按 anthropic > openai > zcode > solvinglab > community 保留', plugins: [...kept.values()].map(v => v.plugin).sort((a, b) => a.name.localeCompare(b.name, 'en')) },
    duplicates: [...duplicates.values()].sort((a, b) => a.name.localeCompare(b.name, 'en')),
  };
}

export async function buildExternal(file = resolve(ROOT, 'data/external.yml')) {
  const data = yaml.load(await readFile(file, 'utf8'));
  if (!data || !Array.isArray(data.items) || !data.provenance) throw new Error('Invalid external.yml');
  const seen = new Set();
  for (const entry of data.items) {
    if (!NAME_PATTERN.test(entry.slug ?? '') || seen.has(entry.slug)) throw new Error(`Invalid or duplicate external slug: ${entry.slug}`);
    seen.add(entry.slug);
    for (const key of ['name', 'publisher', 'summary']) if (!nonEmpty(entry[key])) throw new Error(`External ${entry.slug}: missing ${key}`);
    if (!CATEGORIES.includes(entry.category) || entry.action !== '前往获取') throw new Error(`External ${entry.slug}: invalid category/action`);
    for (const key of ['source', 'homepage', 'registry']) {
      if (key === 'registry' && entry[key] === null) continue;
      let url;
      try { url = new URL(entry[key]); } catch { throw new Error(`External ${entry.slug}: invalid ${key}`); }
      if (url.protocol !== 'https:' || url.username || url.password) throw new Error(`External ${entry.slug}: ${key} must use https`);
    }
  }
  if (data.provenance.observedCount !== data.items.length) throw new Error('External provenance count does not match items');
  return { schemaVersion: 1, kind: 'external-links', provenance: data.provenance, items: data.items };
}

function countsByReason(items) {
  const counts = {};
  for (const item of items) counts[item.reason] = (counts[item.reason] ?? 0) + 1;
  return Object.fromEntries(Object.entries(counts).sort(([a], [b]) => a.localeCompare(b)));
}

export async function build({ client = new GitHub(), now = new Date() } = {}) {
  const mapping = await loadCategories();
  const state = await loadDecayState();
  const external = await buildExternal();
  const readers = [anthropic, openai, zcode, solvinglab];
  const results = await Promise.all(readers.map(reader => reader(client)));
  results.push(await community(client, { now, state }));
  for (const r of results) console.log(`${r.id}: inspected ${r.inspected}, plugin candidates ${r.candidates.length}`);
  const rawCandidates = results.flatMap(r => r.candidates);
  // Check every upstream category, including entries later excluded for a manifest.
  assertMapped(rawCandidates.map(r => r.entry.category), mapping);
  const rejected = results.flatMap(r => r.rejections ?? []);
  const parsed = [];
  for (const candidate of rawCandidates) {
    try {
      const parts = sourceParts(candidate.entry.source, candidate.upstream);
      if (!parts) rejected.push({ id: candidate.id, name: candidate.entry.name, reason: 'non_github' });
      else parsed.push({ ...candidate, parts });
    } catch (error) { rejected.push({ id: candidate.id, name: candidate.entry.name, reason: 'invalid_source', detail: error.message }); }
  }
  await client.metadataBatch(parsed.map(r => r.parts.repo));
  const pinned = [];
  await mapLimit(parsed, 4, async record => {
    const meta = await client.repository(record.parts.repo);
    const reason = meta.notFound ? 'not_found' : meta.private ? 'private_repository' : meta.archived ? 'archived' : !meta.sha ? 'empty_repository' : null;
    if (reason) { rejected.push({ id: record.id, name: record.entry.name, repo: record.parts.repo, reason }); return; }
    // Authentication/network failures abort rather than being counted as delistings.
    const { source } = await client.pin(record.parts);
    pinned.push({ ...record, source });
  });
  console.log(`Reading ${pinned.length} pinned plugin manifests`);
  const manifests = await client.manifests(pinned.map(r => r.source));
  console.log(`Pinned manifests read: ${[...manifests.values()].filter(v => v.manifest).length} valid plugin roots`);
  assertMapped([...manifests.values()].filter(v => v.manifest).flatMap(v => [v.manifest.category, v.manifest.interface?.category]), mapping);
  const records = [];
  const nameCorrections = [];
  for (const record of pinned) {
    const loaded = manifests.get(sourceKey(record.source));
    if (loaded.error) { rejected.push({ id: record.id, name: record.entry.name, source: record.source, reason: loaded.error, detail: loaded.detail }); continue; }
    if (typeof loaded.manifest.name !== 'string' || !NAME_PATTERN.test(loaded.manifest.name)) {
      rejected.push({ id: record.id, name: record.entry.name, source: record.source, reason: 'invalid_manifest_name' }); continue;
    }
    if (record.entry.name && record.entry.name !== loaded.manifest.name) nameCorrections.push({ id: record.id, source: record.source, listedName: record.entry.name, manifestName: loaded.manifest.name });
    records.push(createListing(record, loaded, mapping));
  }
  // A concurrent pin completion must not decide same-source duplicate winners.
  records.sort((a, b) => SOURCE_ORDER.indexOf(a.id) - SOURCE_ORDER.indexOf(b.id) || a.plugin.name.localeCompare(b.plugin.name, 'en') || sourceKey(a.source).localeCompare(sourceKey(b.source), 'en'));
  const subjects = records.map(r => ({ id: r.id, entry: r.plugin }));
  subjects.push(...Object.values(state.entries).flatMap(e => e.subjects));
  const decay = await evaluateDecay(subjects, client, { state, now });
  console.log(`Decay checked: ${decay.summary.healthy} healthy, ${decay.summary.hidden} hidden, ${decay.summary.removed} removed`);
  const surviving = records.filter(record => {
    const decision = decay.decisions.get(`${record.id}:${sourceKey(record.source)}:${record.plugin.name}`);
    if (decision.status === 'healthy') return true;
    const reason = decision.reasons.some(r => ['stars_below_400', 'pushed_over_180_days'].includes(r)) ? 'decay' : decision.reasons[0];
    rejected.push({ id: record.id, name: record.plugin.name, source: record.source, reason, status: decision.status, details: decision.reasons,
      ...(decision.hiddenSince ? { hiddenSince: decision.hiddenSince } : {}) });
    return false;
  });
  const selected = [];
  const seen = new Map(SOURCE_ORDER.map(id => [id, new Set()]));
  for (const record of surviving) {
    if (seen.get(record.id).has(record.plugin.name)) rejected.push({ id: record.id, name: record.plugin.name, source: record.source, reason: 'duplicate_name_within_source' });
    else { seen.get(record.id).add(record.plugin.name); selected.push(record); }
  }
  console.log(`Checking logos for ${selected.length} entries`);
  const logos = await attachLogos(selected, client);
  const markets = Object.fromEntries(SOURCE_ORDER.map(id => [id, { name: marketplaceName(id), description: `OmniMind 公开插件目录：${id}`, plugins: selected.filter(r => r.id === id).map(r => r.plugin) }]));
  const merged = mergeMarkets(markets);
  for (const market of [...Object.values(markets), merged.market]) validateMarketplace(market);
  const declaredByName = new Map();
  for (const r of rawCandidates.filter(r => ['anthropic', 'openai', 'zcode'].includes(r.id) && r.entry.name)) {
    if (!declaredByName.has(r.entry.name)) declaredByName.set(r.entry.name, new Set());
    declaredByName.get(r.entry.name).add(r.id);
  }
  const declaredDuplicates = [...declaredByName.entries()].filter(([, ids]) => ids.size > 1).map(([name]) => name).sort();
  const warnings = [];
  if (external.items.length !== external.provenance.expectedCount) warnings.push(`Referenced website revision contains ${external.items.length} external entries; requested ${external.provenance.expectedCount}. Missing entry requires a source; no placeholder was invented.`);
  const discardedPlugins = rejected.filter(x => x.scope !== 'repository');
  const rejectedRepositories = rejected.filter(x => x.scope === 'repository');
  const report = {
    schemaVersion: 1, generatedAt: now.toISOString(),
    sources: Object.fromEntries(results.map(r => [r.id, { marketplace: marketplaceName(r.id), inspected: r.inspected,
      inspectedUnit: ['solvinglab', 'community'].includes(r.id) ? 'repositories' : 'marketplace_entries',
      candidates: r.candidates.length, accepted: markets[r.id].plugins.length,
      dropped: discardedPlugins.filter(x => x.id === r.id).length,
      rejectedRepositories: rejectedRepositories.filter(x => x.id === r.id).length,
      reasons: countsByReason(discardedPlugins.filter(x => x.id === r.id)),
      repositoryReasons: countsByReason(rejectedRepositories.filter(x => x.id === r.id)),
      ...(r.upstream ? { upstream: r.upstream } : {}), ...(r.inventory ? { inventory: r.inventory } : {}),
      ...(r.searches ? { searches: r.searches, submissions: r.submissions } : {}) }])),
    totalSourceEntries: selected.length, mergedEntries: merged.market.plugins.length,
    droppedPlugins: discardedPlugins.length, rejectedRepositories: rejectedRepositories.length,
    duplicates: { upstreamDeclaredNameCount: declaredDuplicates.length, upstreamDeclaredNames: declaredDuplicates,
      acceptedNameCount: merged.duplicates.length, alternateEntries: merged.duplicates.reduce((n, d) => n + d.alternates.length, 0), retained: merged.duplicates },
    nameCorrections,
    rejected: rejected.sort((a, b) => SOURCE_ORDER.indexOf(a.id) - SOURCE_ORDER.indexOf(b.id) || (a.name ?? a.repo ?? '').localeCompare(b.name ?? b.repo ?? '', 'en')),
    decay: { ...decay.summary, findings: decay.findings.filter(f => f.status !== 'healthy') },
    categories: [...new Set(selected.map(r => r.plugin.category))].sort(), logos,
    external: { count: external.items.length, expected: external.provenance.expectedCount, provenance: external.provenance,
      mapping: external.items.map(e => ({ slug: e.slug, category: e.category })) }, warnings, github: client.stats,
  };
  // Everything above is validated before any tracked artifact is written.
  for (const id of SOURCE_ORDER) await writeJson(resolve(ROOT, `dist/marketplaces/${id}.json`), markets[id]);
  await writeJson(resolve(ROOT, 'dist/plugins.json'), merged.market);
  await writeJson(resolve(ROOT, 'dist/external.json'), external);
  await writeJson(resolve(ROOT, 'dist/report.json'), report);
  await writeJson(STATE_FILE, decay.state);
  console.log(JSON.stringify({ sources: Object.fromEntries(SOURCE_ORDER.map(id => [id, markets[id].plugins.length])), merged: merged.market.plugins.length,
    duplicateNames: merged.duplicates.length, droppedPlugins: discardedPlugins.length, rejectedRepositories: rejectedRepositories.length,
    decay: decay.summary, external: external.items.length, warnings }, null, 2));
  return report;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  build().catch(error => { console.error(error.message); process.exitCode = 1; });
}
