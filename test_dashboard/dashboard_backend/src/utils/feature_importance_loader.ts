import Papa from "papaparse";
import fs from "fs/promises";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const dataDirectory = path.resolve(__dirname, "../..", "data");

const dtFeaturePath = path.join(dataDirectory, "dt_feature_importances.csv");
const logisticFeaturePath = path.join(dataDirectory, "logistic_feature_coefs.csv");
const correlationsPath = path.join(dataDirectory, "correlations_with_churn.json");
const topCorrelationsPath = path.join(dataDirectory, "top_correlations.json");

export interface FeatureImportanceEntry {
  feature: string;
  importance: number;
}

export interface FeatureCoefficientEntry {
  feature: string;
  coefficient: number;
}

export interface TopCorrelationEntry {
  feature: string;
  target: string;
  coefficient: number;
  magnitude_rank: number;
}

export type CorrelationsWithChurn = Record<string, number>;

export interface ModelFeatureImportanceData {
  featureImportances?: FeatureImportanceEntry[];
  featureCoefficients?: FeatureCoefficientEntry[];
  correlationsWithChurn: CorrelationsWithChurn;
  topCorrelations: TopCorrelationEntry[];
}

export interface FeatureImportanceCollection {
  dt: ModelFeatureImportanceData;
  logistic: ModelFeatureImportanceData;
}

let dtImportancesCache: FeatureImportanceEntry[] | null = null;
let logisticCoefficientsCache: FeatureCoefficientEntry[] | null = null;
let correlationsCache: CorrelationsWithChurn | null = null;
let topCorrelationsCache: TopCorrelationEntry[] | null = null;

const parseNumberValue = (value: string | undefined, fieldName: string, rowIndex: number): number => {
  if (value === undefined || value.trim() === "") {
    return 0;
  }

  const numericValue = Number(value);
  if (Number.isNaN(numericValue)) {
    throw new Error(`Invalid numeric value for ${fieldName} at row ${rowIndex + 2}: ${value}`);
  }

  return numericValue;
};

const parseCsvRecords = async <T>(
  filePath: string,
  mapper: (row: Record<string, string>, rowIndex: number) => T
): Promise<T[]> => {
  const rawCsv = await fs.readFile(filePath, "utf-8");
  const parsed = Papa.parse<Record<string, string>>(rawCsv, {
    header: true,
    skipEmptyLines: true,
  });

  if (parsed.errors.length) {
    const [firstError] = parsed.errors;
    throw new Error(`Failed to parse ${path.basename(filePath)} (${firstError.message}) at row ${firstError.row}`);
  }

  return parsed.data.map((row, index) => mapper(row, index));
};

const mapDtRow = (row: Record<string, string>, rowIndex: number): FeatureImportanceEntry => ({
  feature: row[""] ?? "",
  importance: parseNumberValue(row["0"], "importance", rowIndex),
});

const mapLogisticRow = (row: Record<string, string>, rowIndex: number): FeatureCoefficientEntry => ({
  feature: row[""] ?? "",
  coefficient: parseNumberValue(row["0"], "coefficient", rowIndex),
});

const loadJsonAsset = async <T>(filePath: string): Promise<T> => {
  const raw = await fs.readFile(filePath, "utf-8");
  return JSON.parse(raw) as T;
};

export async function loadDtFeatureImportances(): Promise<FeatureImportanceEntry[]> {
  if (dtImportancesCache) {
    return dtImportancesCache;
  }

  dtImportancesCache = await parseCsvRecords<FeatureImportanceEntry>(dtFeaturePath, mapDtRow);
  return dtImportancesCache;
}

export async function loadLogisticFeatureCoefficients(): Promise<FeatureCoefficientEntry[]> {
  if (logisticCoefficientsCache) {
    return logisticCoefficientsCache;
  }

  logisticCoefficientsCache = await parseCsvRecords<FeatureCoefficientEntry>(logisticFeaturePath, mapLogisticRow);
  return logisticCoefficientsCache;
}

export async function loadCorrelationsWithChurn(): Promise<CorrelationsWithChurn> {
  if (correlationsCache) {
    return correlationsCache;
  }

  correlationsCache = await loadJsonAsset<CorrelationsWithChurn>(correlationsPath);
  return correlationsCache;
}

export async function loadTopCorrelations(): Promise<TopCorrelationEntry[]> {
  if (topCorrelationsCache) {
    return topCorrelationsCache;
  }

  topCorrelationsCache = await loadJsonAsset<TopCorrelationEntry[]>(topCorrelationsPath);
  return topCorrelationsCache;
}

export async function loadFeatureImportanceCollection(): Promise<FeatureImportanceCollection> {
  const [featureImportances, featureCoefficients, correlationsWithChurn, topCorrelations] = await Promise.all([
    loadDtFeatureImportances(),
    loadLogisticFeatureCoefficients(),
    loadCorrelationsWithChurn(),
    loadTopCorrelations(),
  ]);

  return {
    dt: {
      featureImportances,
      correlationsWithChurn,
      topCorrelations,
    },
    logistic: {
      featureCoefficients,
      correlationsWithChurn,
      topCorrelations,
    },
  };
}

export function clearFeatureImportanceCache(): void {
  dtImportancesCache = null;
  logisticCoefficientsCache = null;
  correlationsCache = null;
  topCorrelationsCache = null;
}
