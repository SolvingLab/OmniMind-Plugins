import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import * as yaml from 'js-yaml';
import { ROOT } from './github.mjs';

export const CATEGORY_LABELS = { office: '办公文档', coding: '编程开发', design: '设计创作', data: '数据分析', science: '科学研究', collaboration: '协作管理', enhancement: '应用增强' };
export const CATEGORIES = Object.keys(CATEGORY_LABELS);

// Complete English words/phrases and Chinese keywords; name matches weigh
// three times description matches. Ties follow the stable category order.
const KEYWORDS = {
  office: ['document', 'documents', 'documentation', 'docx', 'pdf', 'word', 'excel', 'spreadsheet', 'spreadsheets', 'powerpoint', 'presentation', 'presentations', 'pptx', 'slides', 'writing', 'writer', 'notes', 'notebook', 'obsidian', 'email', 'gmail', 'outlook', 'calendar', 'office', '文件', '文档', '办公', '表格', '幻灯片', '邮件', '日历', '笔记', '写作'],
  coding: ['code', 'coding', 'codebase', 'developer', 'developers', 'development', 'programming', 'software', 'engineering', 'debug', 'debugging', 'test', 'tests', 'testing', 'lint', 'linter', 'refactor', 'refactoring', 'api', 'sdk', 'git', 'github', 'devops', 'deployment', 'deploy', 'frontend', 'backend', 'typescript', 'javascript', 'python', 'rust', 'security', 'vulnerability', 'pull request', 'code review', '编程', '代码', '开发', '调试', '测试', '部署', '重构'],
  design: ['design', 'designer', 'creative', 'creativity', 'figma', 'sketch', 'image', 'images', 'photo', 'photos', 'illustration', 'illustrations', 'video', 'videos', 'animation', 'music', 'audio', 'visual', 'visuals', 'ux', 'ui', 'branding', 'typography', 'canvas', 'capcut', '绘图', '图像', '设计', '创作', '插画', '视频', '音乐', '音频'],
  data: ['data', 'analytics', 'analytical', 'analysis', 'analyze', 'analyse', 'database', 'databases', 'sql', 'mysql', 'postgres', 'postgresql', 'bigquery', 'snowflake', 'databricks', 'pandas', 'statistics', 'statistical', 'dashboard', 'dashboards', 'chart', 'charts', 'finance', 'financial', 'accounting', 'reporting', 'etl', '数据', '分析', '统计', '数据库', '财务', '会计', '报表'],
  science: ['science', 'scientific', 'research', 'researcher', 'academic', 'scholar', 'arxiv', 'pubmed', 'paper', 'papers', 'literature', 'citation', 'citations', 'biology', 'bioinformatics', 'genomics', 'genome', 'chemistry', 'physics', 'math', 'mathematics', 'experiment', 'experiments', 'education', 'learning', '科学', '科研', '研究', '论文', '学术', '文献', '生物', '化学', '物理', '数学'],
  collaboration: ['collaboration', 'collaborate', 'team', 'teams', 'slack', 'discord', 'notion', 'jira', 'linear', 'asana', 'trello', 'meeting', 'meetings', 'project management', 'task', 'tasks', 'supervisor', 'supervision', 'program management', 'workflow', 'workflows', 'operations', 'business', 'sales', 'marketing', 'crm', 'hubspot', 'revenue', 'hiring', 'people', 'pmo', '协作', '团队', '项目管理', '任务', '会议', '业务', '运营', '销售'],
  enhancement: ['agent', 'agents', 'assistant', 'assistants', 'browser', 'browsing', 'search', 'memory', 'context', 'prompt', 'prompts', 'automation', 'automate', 'integration', 'integrations', 'hook', 'hooks', 'harness', 'orchestration', 'terminal', 'cli', 'mcp', 'localization', 'accessibility', '应用', '增强', '浏览器', '搜索', '记忆', '上下文', '提示词', '自动化', '集成', '助手'],
};

function missingCategory(value) {
  return value === undefined || value === null || (typeof value === 'string' && (!value.trim() || value.trim() === 'uncategorized'));
}

function normalizeText(value) {
  return (typeof value === 'string' ? value : '').normalize('NFKC').toLowerCase().replace(/[-_/]+/g, ' ').replace(/\s+/g, ' ');
}

function matches(text, keyword) {
  if (/[^\x00-\x7f]/.test(keyword)) return text.includes(keyword);
  return new RegExp(`(?<![a-z0-9])${keyword}(?![a-z0-9])`, 'u').test(text);
}

export async function loadCategories(file = resolve(ROOT, 'data/categories.yml')) {
  const value = yaml.load(await readFile(file, 'utf8'));
  if (!value || !Array.isArray(value.categories) || value.categories.length !== 7 ||
    new Set(value.categories).size !== 7 || value.categories.some(c => !CATEGORIES.includes(c)) ||
    !value.mapping || typeof value.mapping !== 'object' || Array.isArray(value.mapping)) {
    throw new Error('categories.yml must declare the seven categories and an explicit mapping');
  }
  for (const [from, to] of Object.entries(value.mapping)) {
    if (!CATEGORIES.includes(to)) throw new Error(`Invalid category mapping: ${from} -> ${to}`);
  }
  return value.mapping;
}

export function categoryOf(value, mapping) {
  const raw = missingCategory(value) ? 'uncategorized' : typeof value === 'string' ? value.trim() : value;
  if (typeof raw !== 'string' || !Object.hasOwn(mapping, raw)) throw new Error(`Unmapped category: ${String(raw)}`);
  return mapping[raw];
}

export function classifyCategory(value, mapping, { name = '', description = '' } = {}) {
  if (!missingCategory(value)) return { category: categoryOf(value, mapping), method: 'upstream', inputCategory: value, matches: [] };
  const texts = { name: normalizeText(name), description: normalizeText(description) };
  const candidates = CATEGORIES.map(category => {
    const evidence = KEYWORDS[category].flatMap(keyword => Object.entries(texts)
      .filter(([, text]) => matches(text, keyword)).map(([field]) => ({ keyword, field })));
    return { category, score: evidence.reduce((score, match) => score + (match.field === 'name' ? 3 : 1), 0), matches: evidence };
  }).filter(result => result.score > 0).sort((a, b) => b.score - a.score || CATEGORIES.indexOf(a.category) - CATEGORIES.indexOf(b.category));
  const winner = candidates[0];
  return winner ? { ...winner, method: 'keywords', inputCategory: value ?? null, candidates }
    : { category: 'enhancement', method: 'fallback', inputCategory: value ?? null, matches: [], reason: 'No name or description keywords matched' };
}

export function assertMapped(values, mapping) {
  const missing = [...new Set(values.filter(v => !missingCategory(v) &&
    (typeof v !== 'string' || !Object.hasOwn(mapping, v.trim()))))].sort();
  if (missing.length) throw new Error(`Unmapped categories (add explicit mappings to data/categories.yml): ${missing.map(String).join(', ')}`);
}
