import Papa from 'papaparse';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const dataDirectory = path.resolve(__dirname, '../..', 'data');

const segmentIncomePath = path.join(dataDirectory, 'segment_attrition_income.csv');
const segmentCardPath = path.join(dataDirectory, 'segment_attrition_card.csv');
const segmentSpendQuintilePath = path.join(dataDirectory, 'segment_attrition_spend_quintile.csv');

type SegmentRowBase = {
  total: number;
  churns: number;
  attrition_rate: number;
};

export interface IncomeSegmentRow extends SegmentRowBase {
  Income_Category: string;
}

export interface CardSegmentRow extends SegmentRowBase {
  Card_Category: string;
}

export interface SpendQuintileSegmentRow extends SegmentRowBase {
  spend_quintile: number;
}

let incomeSegmentCache: IncomeSegmentRow[] | null = null;
let cardSegmentCache: CardSegmentRow[] | null = null;
let spendQuintileSegmentCache: SpendQuintileSegmentRow[] | null = null;

const parseNumberValue = (value: string | undefined, fieldName: string, rowIndex: number): number => {
  if (value === undefined || value.trim() === '') {
    return 0;
  }

  const numericValue = Number(value);
  if (Number.isNaN(numericValue)) {
    throw new Error(`Invalid numeric value for ${fieldName} at row ${rowIndex + 2}: ${value}`);
  }

  return numericValue;
};

const parseCsvFile = async <T>(filePath: string, mapper: (row: Record<string, string>, rowIndex: number) => T): Promise<T[]> => {
  const rawCsv = await fs.readFile(filePath, 'utf-8');
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

const mapIncomeRow = (row: Record<string, string>, rowIndex: number): IncomeSegmentRow => ({
  Income_Category: row.Income_Category ?? '',
  total: parseNumberValue(row.total, 'total', rowIndex),
  churns: parseNumberValue(row.churns, 'churns', rowIndex),
  attrition_rate: parseNumberValue(row.attrition_rate, 'attrition_rate', rowIndex),
});

const mapCardRow = (row: Record<string, string>, rowIndex: number): CardSegmentRow => ({
  Card_Category: row.Card_Category ?? '',
  total: parseNumberValue(row.total, 'total', rowIndex),
  churns: parseNumberValue(row.churns, 'churns', rowIndex),
  attrition_rate: parseNumberValue(row.attrition_rate, 'attrition_rate', rowIndex),
});

const mapSpendQuintileRow = (row: Record<string, string>, rowIndex: number): SpendQuintileSegmentRow => ({
  spend_quintile: parseNumberValue(row.spend_quintile, 'spend_quintile', rowIndex),
  total: parseNumberValue(row.total, 'total', rowIndex),
  churns: parseNumberValue(row.churns, 'churns', rowIndex),
  attrition_rate: parseNumberValue(row.attrition_rate, 'attrition_rate', rowIndex),
});

export async function loadIncomeSegmentAttrition(): Promise<IncomeSegmentRow[]> {
  if (incomeSegmentCache) {
    return incomeSegmentCache;
  }

  incomeSegmentCache = await parseCsvFile(segmentIncomePath, mapIncomeRow);
  return incomeSegmentCache;
}

export async function loadCardSegmentAttrition(): Promise<CardSegmentRow[]> {
  if (cardSegmentCache) {
    return cardSegmentCache;
  }

  cardSegmentCache = await parseCsvFile(segmentCardPath, mapCardRow);
  return cardSegmentCache;
}

export async function loadSpendQuintileSegmentAttrition(): Promise<SpendQuintileSegmentRow[]> {
  if (spendQuintileSegmentCache) {
    return spendQuintileSegmentCache;
  }

  spendQuintileSegmentCache = await parseCsvFile(segmentSpendQuintilePath, mapSpendQuintileRow);
  return spendQuintileSegmentCache;
}

export function clearSegmentAttritionCache(): void {
  incomeSegmentCache = null;
  cardSegmentCache = null;
  spendQuintileSegmentCache = null;
}
