import { readMarketplace } from '../lib/github.mjs';
export default client => readMarketplace(client, { id: 'zcode', repo: 'zai-org/zcode-plugins', path: 'marketplace.json' });
