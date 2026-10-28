import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { ROOT, NAME_PATTERN, SHA_PATTERN } from '../lib/github.mjs';

const repo = 'SolvingLab/OmniMind-Plugins';

export default async function selfHosted(client, file = resolve(ROOT, 'data/self-hosted.json')) {
  const data = JSON.parse(await readFile(file, 'utf8'));
  if (!Array.isArray(data.items)) throw new Error('Invalid self-hosted manifest');
  const seen = new Set();
  const candidates = [];
  const rejections = [];
  for (const item of data.items) {
    if (!NAME_PATTERN.test(item.name ?? '') || !SHA_PATTERN.test(item.sha ?? '') || seen.has(item.name)) throw new Error('Invalid or duplicate self-hosted item');
    seen.add(item.name);
    const path = `plugins/${item.name}`;
    const license = await client.file(repo, item.sha, `${path}/LICENSE`);
    if (!license?.trim()) {
      rejections.push({ id: 'self-hosted', name: item.name, reason: 'missing_license' });
      continue;
    }
    const { sha, ...metadata } = item;
    candidates.push({ id: 'self-hosted', entry: { ...metadata, source: { source: 'github', repo, path, sha } } });
  }
  return { id: 'self-hosted', inspected: data.items.length, candidates, rejections };
}
