import Papa from 'papaparse';
import fs from 'fs/promises';
import path from 'path';
import type { CleanedRow } from '../models/data_types.js';

const CLEANED_PATH = path.resolve(process.cwd(), 'data', 'cleaned.csv');

let cleanedCache: Promise<CleanedRow[]> | null = null;

export async function loadCleanedData(): Promise<CleanedRow[]> {
  if (cleanedCache) return cleanedCache;

  cleanedCache = (async (): Promise<CleanedRow[]> => {
    const raw = await fs.readFile(CLEANED_PATH, 'utf8');
    const parsed = Papa.parse<CleanedRow>(raw, { header: true, dynamicTyping: true, skipEmptyLines: true });

    if (parsed.errors && parsed.errors.length > 0) {
      // throw the first parsing error
      throw new Error(`CSV parse error: ${parsed.errors[0].message}`);
    }

    const rows = parsed.data.map((r) => {
      // Ensure core typed columns have correct types
      const churn = r.churn ?? 0;
      const monthly_spend = r.monthly_spend ?? 0;
      const tenure_months = r.tenure_months ?? r.Months_on_book ?? 0;
      const spend_quintile = r.spend_quintile ?? 0;

      const normalized: CleanedRow = {
        ...(r as CleanedRow),
        churn,
        monthly_spend,
        tenure_months,
        spend_quintile,
      };

      return normalized;
    });

    return rows;
  })();

  return cleanedCache;
}
