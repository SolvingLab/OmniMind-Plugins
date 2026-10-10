import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import * as yaml from 'js-yaml';
import { ROOT } from './github.mjs';

export const CATEGORIES = ['办公文档', '编程开发', '设计创作', '数据分析', '科学研究', '协作管理', '应用增强'];

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
  const raw = value ?? 'uncategorized';
  if (typeof raw !== 'string' || !Object.hasOwn(mapping, raw)) throw new Error(`Unmapped category: ${String(raw)}`);
  return mapping[raw];
}

export function assertMapped(values, mapping) {
  const missing = [...new Set(values.filter(v => v !== undefined && v !== null &&
    (typeof v !== 'string' || !Object.hasOwn(mapping, v))))].sort();
  if (missing.length) throw new Error(`Unmapped categories (add explicit mappings to data/categories.yml): ${missing.map(String).join(', ')}`);
}
