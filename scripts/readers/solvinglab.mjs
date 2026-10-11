import { mapLimit, MANIFESTS } from '../lib/github.mjs';

export function manifestRoots(paths) {
  const roots = new Set();
  for (const path of paths) {
    for (const manifest of MANIFESTS) {
      if (path === manifest) roots.add('');
      else if (path.endsWith(`/${manifest}`)) roots.add(path.slice(0, -manifest.length - 1));
    }
  }
  return [...roots].sort();
}

export default async function solvinglab(client) {
  const repos = await client.publicOrgRepos('SolvingLab');
  await client.metadataBatch(repos);
  const inventory = await mapLimit(repos, 4, async repo => {
    const meta = await client.repository(repo);
    if (meta.private || meta.notFound || !meta.sha) return { repo, roots: [], reason: 'unavailable_repository' };
    const roots = manifestRoots(await client.tree(repo, meta.sha));
    return { repo: meta.repo, sha: meta.sha, roots, ...(roots.length ? {} : { reason: 'unsupported_manifest' }) };
  });
  return {
    id: 'solvinglab', inspected: inventory.length,
    inventory,
    candidates: inventory.flatMap(item => item.roots.map(path => ({ id: 'solvinglab', entry: { source: { source: 'github', repo: item.repo, path, sha: item.sha } } }))),
    rejections: inventory.filter(item => item.reason).map(item => ({ id: 'solvinglab', scope: 'repository', repo: item.repo, reason: item.reason, detail: 'recursive public repository inventory; no supported plugin root' })),
  };
}
