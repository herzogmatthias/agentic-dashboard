import Papa from 'papaparse';
import fs from 'fs/promises';
import path from 'path';
import type { FeatureImportancesByModel, FeatureImportanceEntry } from '../models/data_types.js';

const DATA_DIR = path.resolve(process.cwd(), 'data');

let cache: Partial<Record<string, Promise<any>>> = {};

async function loadCSV<T>(filename: string): Promise<T[]> {
  if (cache[filename]) return cache[filename];
  const p = (async (): Promise<T[]> => {
    const full = path.join(DATA_DIR, filename);
    const raw = await fs.readFile(full, 'utf8');
    const parsed = Papa.parse<T>(raw, { header: true, dynamicTyping: true, skipEmptyLines: true });
    if (parsed.errors && parsed.errors.length > 0) throw new Error(parsed.errors[0].message);
    return parsed.data;
  })();
  cache[filename] = p;
  return p;
}

export async function loadFeatureImportances(): Promise<FeatureImportancesByModel> {
  const dt = await loadCSV<FeatureImportanceEntry>('dt_feature_importances.csv');
  const lg = await loadCSV<FeatureImportanceEntry>('logistic_feature_coefs.csv');
  const corRaw = await fs.readFile(path.join(DATA_DIR, 'correlations_with_churn.json'), 'utf8');
  const cor = JSON.parse(corRaw) as { [k: string]: number };
  const topRaw = await fs.readFile(path.join(DATA_DIR, 'top_correlations.json'), 'utf8');
  const top = JSON.parse(topRaw) as { feature: string; correlation: number }[];

  const out: FeatureImportancesByModel = {
    decision_tree: { dt_feature_importances: dt, correlations_with_churn: cor, top_correlations: top },
    logistic: { logistic_feature_coefs: lg, correlations_with_churn: cor, top_correlations: top },
  };

  return out;
}
