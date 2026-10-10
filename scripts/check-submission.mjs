import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { GitHub, NAME_PATTERN, sourceKey } from './lib/github.mjs';
import { readSubmission, submissionFiles, inspectCommunityRepo } from './readers/community.mjs';

export async function checkSubmissions(files, client = new GitHub()) {
  const targets = files.length ? files.map(f => resolve(f)) : await submissionFiles();
  if (!targets.length) { console.log('No submission files to check'); return { checked: 0, failed: 0 }; }
  const submissions = await Promise.all(targets.map(async file => ({ file, value: await readSubmission(file) })));
  await client.metadataBatch(submissions.map(s => s.value.repo));
  let failed = 0;
  for (const { file, value } of submissions) {
    const inspected = await inspectCommunityRepo(client, value.repo);
    const problems = [...inspected.problems];
    let source;
    let loaded;
    if (!problems.length) {
      ({ source } = await client.pin(value));
      loaded = (await client.manifests([source])).get(sourceKey(source));
      if (loaded.error) problems.push(loaded.error);
      else if (typeof loaded.manifest.name !== 'string' || !NAME_PATTERN.test(loaded.manifest.name)) problems.push('invalid_manifest_name');
      // A formerly valid pin cannot bypass a removed manifest on HEAD.
      if (!inspected.roots.includes(source.path)) problems.push('manifest_missing_on_head');
      else if (!loaded.error) {
        const head = { ...source, sha: inspected.meta.sha };
        const current = (await client.manifests([head])).get(sourceKey(head));
        if (current.error) problems.push(current.error);
        else if (current.manifest.name !== loaded.manifest.name) problems.push('name_mismatch_on_head');
      }
    }
    if (problems.length) { failed++; console.error(`FAIL ${file}: ${problems.join(', ')}`); }
    else console.log(`PASS ${file}: ${loaded.manifest.name} <- ${source.repo}/${source.path || '.'}@${source.sha} (${loaded.manifestPath})`);
  }
  console.log(`${targets.length - failed}/${targets.length} submissions pass`);
  return { checked: targets.length, failed };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  checkSubmissions(process.argv.slice(2)).then(result => { if (result.failed) process.exitCode = 1; }).catch(error => { console.error(error.message); process.exitCode = 1; });
}
