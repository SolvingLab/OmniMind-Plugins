import { readMarketplace } from '../lib/github.mjs';
export default client => readMarketplace(client, { id: 'anthropic', repo: 'anthropics/claude-plugins-official', path: '.claude-plugin/marketplace.json' });
