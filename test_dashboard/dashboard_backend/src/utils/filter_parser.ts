export const IncomeCategories = [
  "Less than $40K",
  "$40K - $60K",
  "$60K - $80K",
  "$80K - $120K",
  "$120K +",
];

export const CardCategories = ["Blue", "Silver", "Gold", "Platinum"];

export interface GlobalFilters {
  incomeCategories?: string[];
  cardCategories?: string[];
  spendQuintiles?: number[];
  tenureRange?: { min: number; max: number };
}

export interface ParsedFilters {
  incomeCategories?: string[];
  cardCategories?: string[];
  spendQuintiles?: number[];
  tenureRange?: { min: number; max: number };
}

const parseCommaSeparatedValues = (value?: string): string[] | undefined => {
  if (!value) {
    return undefined;
  }

  return value
    .split(",")
    .map((segment) => segment.trim())
    .filter((segment) => segment.length > 0);
};

const parseSpendQuintiles = (value?: string): number[] | undefined => {
  const segments = parseCommaSeparatedValues(value);
  if (!segments || segments.length === 0) {
    return undefined;
  }

  return segments
    .map((segment) => Number(segment))
    .filter((numberValue) => Number.isFinite(numberValue) && numberValue >= 0 && numberValue <= 4)
    .map((numberValue) => Math.round(numberValue));
};

const parseTenureRange = (value?: string): { min: number; max: number } | undefined => {
  if (!value) {
    return undefined;
  }

  const segments = value
    .split(",")
    .map((segment) => segment.trim())
    .filter((segment) => segment.length > 0);

  if (segments.length !== 2) {
    throw new Error("tenure_months must be defined as min,max");
  }

  const min = Number(segments[0]);
  const max = Number(segments[1]);

  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    throw new Error("tenure_months range must contain valid numbers");
  }

  if (min < 0 || max < 0) {
    throw new Error("tenure_months values must be >= 0");
  }

  if (min > max) {
    throw new Error("tenure_months min must be <= max");
  }

  return { min, max };
};

export function parseGlobalFilters(query: Record<string, string | undefined>): ParsedFilters {
  const filters: ParsedFilters = {};

  const incomeValues = parseCommaSeparatedValues(query.Income_Category);
  if (incomeValues && incomeValues.length) {
    filters.incomeCategories = incomeValues.filter((value) => IncomeCategories.includes(value));
  }

  const cardValues = parseCommaSeparatedValues(query.Card_Category);
  if (cardValues && cardValues.length) {
    filters.cardCategories = cardValues.filter((value) => CardCategories.includes(value));
  }

  const spendQuintileValues = parseSpendQuintiles(query.spend_quintile);
  if (spendQuintileValues && spendQuintileValues.length) {
    filters.spendQuintiles = spendQuintileValues;
  }

  const tenureRange = parseTenureRange(query.tenure_months);
  if (tenureRange) {
    filters.tenureRange = tenureRange;
  }

  return filters;
}

export function parseKpiFilters(query: Record<string, string | undefined>): ParsedFilters {
  const filters: ParsedFilters = {};

  const incomeValues = parseCommaSeparatedValues(query.incomeCategories);
  if (incomeValues && incomeValues.length) {
    filters.incomeCategories = incomeValues.filter((value) => IncomeCategories.includes(value));
  }

  const cardValues = parseCommaSeparatedValues(query.cardCategories);
  if (cardValues && cardValues.length) {
    filters.cardCategories = cardValues.filter((value) => CardCategories.includes(value));
  }

  const spendQuintileValues = parseSpendQuintiles(query.spendQuintiles);
  if (spendQuintileValues && spendQuintileValues.length) {
    filters.spendQuintiles = spendQuintileValues;
  }

  const tenureMin = query.tenureMin ? Number(query.tenureMin) : undefined;
  const tenureMax = query.tenureMax ? Number(query.tenureMax) : undefined;
  if (tenureMin !== undefined && tenureMax !== undefined && Number.isFinite(tenureMin) && Number.isFinite(tenureMax) && tenureMin <= tenureMax && tenureMin >= 0 && tenureMax >= 0) {
    filters.tenureRange = { min: tenureMin, max: tenureMax };
  }

  return filters;
}
