import fs from 'fs/promises';
import path from 'path';
const DATA_DIR = path.resolve(process.cwd(), 'data');
let metricsCache = {};
export async function loadKeyMetrics() {
    if (metricsCache.keyMetrics)
        return metricsCache.keyMetrics;
    metricsCache.keyMetrics = (async () => {
        const p = path.join(DATA_DIR, 'key_metrics.json');
        const raw = await fs.readFile(p, 'utf8');
        return JSON.parse(raw);
    })();
    return metricsCache.keyMetrics;
}
export async function loadSummaryMetrics() {
    if (metricsCache.summaryMetrics)
        return metricsCache.summaryMetrics;
    metricsCache.summaryMetrics = (async () => {
        const p = path.join(DATA_DIR, 'summary_metrics.json');
        const raw = await fs.readFile(p, 'utf8');
        return JSON.parse(raw);
    })();
    return metricsCache.summaryMetrics;
}
