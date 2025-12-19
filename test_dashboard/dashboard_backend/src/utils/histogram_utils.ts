import type { CleanedDataRow } from "./cleaned_data_loader.js";

export interface HistogramBin {
  min: number;
  max: number;
  count: number;
}

type NumericAccessor = (row: CleanedDataRow) => number;

function deriveBounds(data: number[]): { min: number; max: number } {
  if (data.length === 0) {
    return { min: 0, max: 0 };
  }

  return {
    min: Math.min(...data),
    max: Math.max(...data),
  };
}

export function buildHistogram(
  data: CleanedDataRow[],
  accessor: NumericAccessor,
  options: { binCount?: number; binWidth?: number } = {}
): HistogramBin[] {
  const numericValues = data.map(accessor);
  if (numericValues.length === 0) {
    return [];
  }

  const { min, max } = deriveBounds(numericValues);
  const defaultBinCount = 10;
  const binCount = options.binCount ?? defaultBinCount;
  const binWidth = options.binWidth ?? (max - min) / binCount;

  if (binWidth <= 0) {
    return [
      {
        min,
        max,
        count: numericValues.length,
      },
    ];
  }

  const bins: HistogramBin[] = [];
  for (let i = 0; i < binCount; i += 1) {
    const binMin = min + i * binWidth;
    const binMax = i === binCount - 1 ? max : binMin + binWidth;
    bins.push({
      min: binMin,
      max: binMax,
      count: 0,
    });
  }

  numericValues.forEach((value) => {
    const index = Math.min(
      binCount - 1,
      Math.floor((value - min) / binWidth)
    );

    bins[index].count += 1;
  });

  return bins;
}
