import { posix } from 'node:path';
import { normalizePath, mapLimit } from './github.mjs';

export function rawUrl(source, path) {
  return `https://raw.githubusercontent.com/${source.repo}/${source.sha}/${normalizePath(path).split('/').map(encodeURIComponent).join('/')}`;
}

// Availability probes contain no Authorization header, including third-party icons.
export async function availableHttps(url) {
  let parsed;
  try { parsed = new URL(url); } catch { return false; }
  if (parsed.protocol !== 'https:' || parsed.username || parsed.password) return false;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const r = await fetch(url, { method: 'GET', signal: AbortSignal.timeout(12_000), redirect: 'follow' });
      const final = new URL(r.url);
      const ok = r.ok && final.protocol === 'https:' && /^image\//i.test(r.headers.get('content-type') ?? '');
      await r.body?.cancel();
      if (ok) return true;
      if (r.status !== 429 && r.status < 500) return false;
    } catch { /* A missing icon never invalidates a plugin. */ }
  }
  return false;
}

export async function attachLogos(records, client) {
  const probes = new Map();
  const probe = url => {
    if (!probes.has(url)) probes.set(url, availableHttps(url));
    return probes.get(url);
  };
  await mapLimit(records, 6, async record => {
    const { plugin, manifest } = record;
    const source = plugin.source;
    const value = record.entry.icon ?? manifest.icon ?? manifest.interface?.logo;
    let url;
    if (typeof value === 'string' && value) {
      if (/^https:\/\//i.test(value)) url = value;
      else if (!/^[a-z][a-z0-9+.-]*:/i.test(value)) {
        try {
          // Codex interface.logo is relative to the plugin root; also accept
          // manifest-relative assets when the upstream stores them there.
          const path = normalizePath(value);
          const paths = await client.tree(source.repo, source.sha);
          const candidates = [posix.join(source.path, path), posix.join(posix.dirname(record.manifestPath), path)];
          const found = candidates.find(p => paths.includes(p));
          if (found) url = rawUrl(source, found);
        } catch (error) {
          if (!error.message.startsWith('Invalid repository-relative') && !error.message.startsWith('Unsafe repository-relative')) throw error;
        }
      }
    }
    if (url && await probe(url)) plugin.icon = url;
    else {
      const fallback = `https://github.com/${source.repo.split('/')[0]}.png`;
      if (await probe(fallback)) plugin.icon = fallback;
    }
  });
  return { checked: probes.size, withIcon: records.filter(r => r.plugin.icon).length };
}
