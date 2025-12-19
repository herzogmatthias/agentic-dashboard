import Papa from 'papaparse';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import { z } from 'zod';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const dataDirectory = path.resolve(__dirname, '../..', 'data');
const cleanedCsvPath = path.join(dataDirectory, 'cleaned.csv');

export interface CleanedDataRow {
  CLIENTNUM: string;
  Attrition_Flag: string;
  Customer_Age: number;
  Gender: string;
  Dependent_count: number;
  Education_Level: string;
  Marital_Status: string;
  Income_Category: string;
  Card_Category: string;
  Months_on_book: number;
  Total_Relationship_Count: number;
  Months_Inactive_12_mon: number;
  Contacts_Count_12_mon: number;
  Credit_Limit: number;
  Total_Revolving_Bal: number;
  Avg_Open_To_Buy: number;
  Total_Amt_Chng_Q4_Q1: number;
  Total_Trans_Amt: number;
  Total_Trans_Ct: number;
  Total_Ct_Chng_Q4_Q1: number;
  Avg_Utilization_Ratio: number;
  churn: number;
  monthly_spend: number;
  avg_txn_value: number;
  tenure_months: number;
  spend_quintile: number;
}

let cleanedDataCache: CleanedDataRow[] | null = null;

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

const mapCleanedRow = (row: Record<string, string>, rowIndex: number): CleanedDataRow => ({
  CLIENTNUM: row.CLIENTNUM ?? '',
  Attrition_Flag: row.Attrition_Flag ?? '',
  Customer_Age: parseNumberValue(row.Customer_Age, 'Customer_Age', rowIndex),
  Gender: row.Gender ?? '',
  Dependent_count: parseNumberValue(row.Dependent_count, 'Dependent_count', rowIndex),
  Education_Level: row.Education_Level ?? '',
  Marital_Status: row.Marital_Status ?? '',
  Income_Category: row.Income_Category ?? '',
  Card_Category: row.Card_Category ?? '',
  Months_on_book: parseNumberValue(row.Months_on_book, 'Months_on_book', rowIndex),
  Total_Relationship_Count: parseNumberValue(row.Total_Relationship_Count, 'Total_Relationship_Count', rowIndex),
  Months_Inactive_12_mon: parseNumberValue(row.Months_Inactive_12_mon, 'Months_Inactive_12_mon', rowIndex),
  Contacts_Count_12_mon: parseNumberValue(row.Contacts_Count_12_mon, 'Contacts_Count_12_mon', rowIndex),
  Credit_Limit: parseNumberValue(row.Credit_Limit, 'Credit_Limit', rowIndex),
  Total_Revolving_Bal: parseNumberValue(row.Total_Revolving_Bal, 'Total_Revolving_Bal', rowIndex),
  Avg_Open_To_Buy: parseNumberValue(row.Avg_Open_To_Buy, 'Avg_Open_To_Buy', rowIndex),
  Total_Amt_Chng_Q4_Q1: parseNumberValue(row.Total_Amt_Chng_Q4_Q1, 'Total_Amt_Chng_Q4_Q1', rowIndex),
  Total_Trans_Amt: parseNumberValue(row.Total_Trans_Amt, 'Total_Trans_Amt', rowIndex),
  Total_Trans_Ct: parseNumberValue(row.Total_Trans_Ct, 'Total_Trans_Ct', rowIndex),
  Total_Ct_Chng_Q4_Q1: parseNumberValue(row.Total_Ct_Chng_Q4_Q1, 'Total_Ct_Chng_Q4_Q1', rowIndex),
  Avg_Utilization_Ratio: parseNumberValue(row.Avg_Utilization_Ratio, 'Avg_Utilization_Ratio', rowIndex),
  churn: parseNumberValue(row.churn, 'churn', rowIndex),
  monthly_spend: parseNumberValue(row.monthly_spend, 'monthly_spend', rowIndex),
  avg_txn_value: parseNumberValue(row.avg_txn_value, 'avg_txn_value', rowIndex),
  tenure_months: parseNumberValue(row.tenure_months, 'tenure_months', rowIndex),
  spend_quintile: parseNumberValue(row.spend_quintile, 'spend_quintile', rowIndex),
});

export async function loadCleanedData(): Promise<CleanedDataRow[]> {
  if (cleanedDataCache) {
    return cleanedDataCache;
  }

  const rawCsv = await fs.readFile(cleanedCsvPath, 'utf-8');
  const parsed = Papa.parse<Record<string, string>>(rawCsv, {
    header: true,
    skipEmptyLines: true,
  });

  if (parsed.errors.length) {
    const [firstError] = parsed.errors;
    throw new Error(`Failed to parse cleaned.csv (${firstError.message}) at row ${firstError.row}`);
  }

  cleanedDataCache = parsed.data.map((row, index) => mapCleanedRow(row, index));
  return cleanedDataCache;
}

export function clearCleanedDataCache(): void {
  cleanedDataCache = null;
}
