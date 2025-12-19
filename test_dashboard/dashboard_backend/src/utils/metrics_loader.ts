import fs from "fs/promises";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const dataDirectory = path.resolve(__dirname, "../..", "data");

const keyMetricsPath = path.join(dataDirectory, "key_metrics.json");
const summaryMetricsPath = path.join(dataDirectory, "summary_metrics.json");

export interface KeyMetrics {
  overall_attrition_rate: number;
  rows: number;
  cols: number;
}

export interface SummaryMetrics {
  rows_before: number;
  rows_after: number;
  overall_attrition_rate: number;
  num_columns_raw: number;
  num_columns_clean: number;
}

let keyMetricsCache: KeyMetrics | null = null;
let summaryMetricsCache: SummaryMetrics | null = null;

async function loadJsonFile<T>(filePath: string): Promise<T> {
  const raw = await fs.readFile(filePath, "utf-8");
  return JSON.parse(raw) as T;
}

export async function loadKeyMetrics(): Promise<KeyMetrics> {
  if (keyMetricsCache) {
    return keyMetricsCache;
  }

  keyMetricsCache = await loadJsonFile<KeyMetrics>(keyMetricsPath);
  return keyMetricsCache;
}

export async function loadSummaryMetrics(): Promise<SummaryMetrics> {
  if (summaryMetricsCache) {
    return summaryMetricsCache;
  }

  summaryMetricsCache = await loadJsonFile<SummaryMetrics>(summaryMetricsPath);
  return summaryMetricsCache;
}

export function clearMetricsCache(): void {
  keyMetricsCache = null;
  summaryMetricsCache = null;
}
