import Papa from 'papaparse';
import fs from 'fs/promises';
import path from 'path';

export interface SegmentRow {
  segment: string;
  attrited_count: number;
  total_customers: number;
  attrition_rate?: number;
  [key: string]: string | number | undefined;
}

const BASE_DIR = path.resolve(process.cwd(), 'data');

let cache: Partial<Record<string, Promise<SegmentRow[]>>> = {};

async function loadCSV(filename: string): Promise<SegmentRow[]> {
  if (cache[filename]) return cache[filename];
  const p = (async (): Promise<SegmentRow[]> => {
    const full = path.join(BASE_DIR, filename);
    const raw = await fs.readFile(full, 'utf8');
    const parsed = Papa.parse<SegmentRow>(raw, { header: true, dynamicTyping: true, skipEmptyLines: true });
    if (parsed.errors && parsed.errors.length > 0) throw new Error(parsed.errors[0].message);
    const rows = parsed.data.map((r) => ({
      ...r,
      attrited_count: r.attrited_count ?? 0,
      total_customers: r.total_customers ?? 0,
      attrition_rate: r.attrition_rate ?? ((r.attrited_count ?? 0) / Math.max(1, (r.total_customers ?? 1))),
    }));
    return rows;
  })();
  cache[filename] = p;
  return p;
}

export async function loadSegmentAttritionByIncome(): Promise<SegmentRow[]> {
  return loadCSV('segment_attrition_income.csv');
}

export async function loadSegmentAttritionByCard(): Promise<SegmentRow[]> {
  return loadCSV('segment_attrition_card.csv');
}

export async function loadSegmentAttritionBySpendQuintile(): Promise<SegmentRow[]> {
  return loadCSV('segment_attrition_spend_quintile.csv');
}
