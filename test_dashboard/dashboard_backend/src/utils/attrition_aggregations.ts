import type { CleanedRow, AttritionAggResult } from '../models/data_types.js';

export function aggregateAttrition(rows: CleanedRow[], groupBy?: keyof CleanedRow): AttritionAggResult[] {
  if (!groupBy) {
    const total_customers = rows.length;
    const attrited_count = rows.reduce((acc, r) => acc + (r.churn ? r.churn : 0), 0);
    const attrition_rate = total_customers === 0 ? 0 : attrited_count / total_customers;
    return [{ attrited_count, total_customers, attrition_rate }];
  }

  const groups = new Map<string, { attrited_count: number; total_customers: number }>();

  for (const r of rows) {
    const keyRaw = r[groupBy];
    const key = keyRaw === undefined || keyRaw === null ? 'UNKNOWN' : String(keyRaw);
    const cur = groups.get(key) ?? { attrited_count: 0, total_customers: 0 };
    cur.total_customers += 1;
    cur.attrited_count += r.churn ? r.churn : 0;
    groups.set(key, cur);
  }

  const results: AttritionAggResult[] = [];
  for (const [group, v] of groups.entries()) {
    results.push({ group, attrited_count: v.attrited_count, total_customers: v.total_customers, attrition_rate: v.total_customers === 0 ? 0 : v.attrited_count / v.total_customers });
  }
  return results;
}
