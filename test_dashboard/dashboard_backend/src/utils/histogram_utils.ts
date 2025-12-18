import type { CleanedRow, HistogramBin } from '../models/data_types.js';

export interface HistogramOptions {
  bins?: number;
  binWidth?: number;
  valueAccessor?: (r: CleanedRow) => number;
}

export function histogram(rows: CleanedRow[], measure: string, options?: HistogramOptions): HistogramBin[] {
  const accessor = options?.valueAccessor ?? ((r: CleanedRow) => Number((r as any)[measure] ?? 0));
  const values = rows.map(accessor).filter((v) => Number.isFinite(v));
  if (values.length === 0) return [];

  const min = Math.min(...values);
  const max = Math.max(...values);
  const bins = options?.bins ?? 20;

  let binWidth = options?.binWidth;
  if (binWidth === undefined) {
    binWidth = (max - min) / bins || 1;
  }

  const edges: number[] = [];
  for (let i = 0; i <= bins; i++) edges.push(min + i * binWidth);

  const counts = new Array(edges.length - 1).fill(0);
  for (const v of values) {
    let idx = Math.floor((v - min) / binWidth);
    if (idx < 0) idx = 0;
    if (idx >= counts.length) idx = counts.length - 1;
    counts[idx] += 1;
  }

  const result: HistogramBin[] = [];
  for (let i = 0; i < counts.length; i++) {
    result.push({ x0: edges[i], x1: edges[i + 1], count: counts[i] });
  }

  return result;
}
