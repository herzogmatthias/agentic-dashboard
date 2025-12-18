import type { Filter } from '../models/data_types.js';

function toStringArray(val: unknown): string[] | undefined {
  if (val === undefined || val === null) return undefined;
  if (Array.isArray(val)) return val.map((v) => (typeof v === 'string' ? v : String(v)));
  return [typeof val === 'string' ? val : String(val)];
}

function toNumberArray(val: unknown): number[] | undefined {
  if (val === undefined || val === null) return undefined;
  const arr = Array.isArray(val) ? val : [val];
  const nums = arr
    .map((v) => {
      if (typeof v === 'number') return v;
      if (typeof v === 'string') {
        const n = Number(v);
        return Number.isNaN(n) ? null : n;
      }
      return null;
    })
    .filter((n): n is number => n !== null);
  return nums.length > 0 ? nums : undefined;
}

export function parseFilters(query: Record<string, unknown>): Filter {
  const incomeCategories = toStringArray(query.Income_Category);
  const cardCategories = toStringArray(query.Card_Category);
  const spendQuintiles = toNumberArray(query.spend_quintile);

  const tenureMonths: Filter['tenureMonths'] = {};
  if (query.tenure_months_min !== undefined && query.tenure_months_min !== null) {
    const min = typeof query.tenure_months_min === 'number' ? query.tenure_months_min : Number(String(query.tenure_months_min));
    if (!Number.isNaN(min)) tenureMonths.min = min;
  }
  if (query.tenure_months_max !== undefined && query.tenure_months_max !== null) {
    const max = typeof query.tenure_months_max === 'number' ? query.tenure_months_max : Number(String(query.tenure_months_max));
    if (!Number.isNaN(max)) tenureMonths.max = max;
  }

  const filter: Filter = {
    incomeCategories: incomeCategories ?? undefined,
    cardCategories: cardCategories ?? undefined,
    spendQuintiles: spendQuintiles ?? undefined,
    tenureMonths: Object.keys(tenureMonths).length > 0 ? tenureMonths : undefined,
  };

  return filter;
}
