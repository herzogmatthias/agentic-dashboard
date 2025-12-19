import type { CleanedDataRow } from "./cleaned_data_loader.js";

type AggregationBucket<T extends string> = Record<T, {
  totalCustomers: number;
  attritedCount: number;
  attritionRate: number;
}>;

export interface AttritionMetrics {
  totalCustomers: number;
  attritedCount: number;
  attritionRate: number;
}

export function aggregateAttrition(data: CleanedDataRow[]): AttritionMetrics {
  const totalCustomers = data.length;
  const attritedCount = data.filter((row) => row.churn === 1).length;
  const attritionRate = totalCustomers === 0 ? 0 : attritedCount / totalCustomers;

  return {
    totalCustomers,
    attritedCount,
    attritionRate,
  };
}

export function aggregateAttritionByDimension<Dimension extends string>(
  data: CleanedDataRow[],
  dimensionAccessor: (row: CleanedDataRow) => Dimension
): AggregationBucket<Dimension> {
  const bucket: AggregationBucket<Dimension> = {} as AggregationBucket<Dimension>;

  data.forEach((row) => {
    const dimensionValue = dimensionAccessor(row);

    if (!bucket[dimensionValue]) {
      bucket[dimensionValue] = {
        totalCustomers: 0,
        attritedCount: 0,
        attritionRate: 0,
      };
    }

    bucket[dimensionValue].totalCustomers += 1;
    if (row.churn === 1) {
      bucket[dimensionValue].attritedCount += 1;
    }
  });

  (Object.keys(bucket) as Dimension[]).forEach((key) => {
    const entry = bucket[key];
    entry.attritionRate = entry.totalCustomers === 0 ? 0 : entry.attritedCount / entry.totalCustomers;
  });

  return bucket;
}
