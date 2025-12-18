export interface CleanedRow {
  CLIENTNUM: number;
  Attrition_Flag: string;
  Customer_Age?: number;
  Gender?: string;
  Dependent_count?: number;
  Education_Level?: string;
  Marital_Status?: string;
  Income_Category?: string;
  Card_Category?: string;
  Months_on_book?: number;
  Total_Relationship_Count?: number;
  Months_Inactive_12_mon?: number;
  Contacts_Count_12_mon?: number;
  Credit_Limit?: number;
  Total_Revolving_Bal?: number;
  Avg_Open_To_Buy?: number;
  Total_Amt_Chng_Q4_Q1?: number;
  Total_Trans_Amt?: number;
  Total_Trans_Ct?: number;
  Total_Ct_Chng_Q4_Q1?: number;
  Avg_Utilization_Ratio?: number;

  // Core typed columns required by the dashboard
  churn: number; // 0/1
  monthly_spend: number;
  avg_txn_value?: number;
  tenure_months: number;
  spend_quintile: number;

  [key: string]: string | number | undefined;
}

export interface Filter {
  incomeCategories?: string[];
  cardCategories?: string[];
  spendQuintiles?: number[];
  tenureMonths?: { min?: number; max?: number };
}

export interface AttritionAggResult {
  group?: string | number;
  attrited_count: number;
  total_customers: number;
  attrition_rate: number; // 0..1
}

export interface HistogramBin {
  x0: number;
  x1: number;
  count: number;
}

export type GenericRecord = { [key: string]: string | number | undefined };

export interface FeatureImportanceEntry {
  feature: string;
  importance?: number;
  coef?: number;
  model_source?: string;
  [key: string]: string | number | undefined;
}

export interface FeatureImportancesByModel {
  [modelSource: string]: {
    dt_feature_importances?: FeatureImportanceEntry[];
    logistic_feature_coefs?: FeatureImportanceEntry[];
    correlations_with_churn?: { [feature: string]: number } | null;
    top_correlations?: { feature: string; correlation: number }[] | null;
  };
}
