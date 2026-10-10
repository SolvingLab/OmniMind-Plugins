import { readMarketplace } from '../lib/github.mjs';
export default client => readMarketplace(client, { id: 'openai', repo: 'openai/plugins', path: '.agents/plugins/marketplace.json' });
