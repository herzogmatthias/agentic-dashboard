import { z, createRoute, OpenAPIHono } from '@hono/zod-openapi';
import { loadCleanedData } from '../../utils/cleaned_data_loader.js';
import type { CleanedDataRow } from '../../utils/cleaned_data_loader.js';
import { parseKpiFilters } from '../../utils/filter_parser.js';
import { applyGlobalFilters } from '../../utils/filter_applicator.js';
import { aggregateAttrition } from '../../utils/attrition_aggregations.js';
import { formatPercentage, formatInteger, formatCurrency, calculateMedian } from '../../utils/formatters.js';

const QuerySchema = z.object({
  incomeCategories: z.string().openapi({ param: { name: 'incomeCategories', in: 'query', required: false } }),
  cardCategories: z.string().openapi({ param: { name: 'cardCategories', in: 'query', required: false } }),
  spendQuintiles: z.string().openapi({ param: { name: 'spendQuintiles', in: 'query', required: false } }),
  tenureMin: z.coerce.number().openapi({ param: { name: 'tenureMin', in: 'query', required: false } }).optional(),
  tenureMax: z.coerce.number().openapi({ param: { name: 'tenureMax', in: 'query', required: false } }).optional(),
});

const AttritionRateKpiSchema = z.object({
  value: z.number().openapi({ example: 0.162 }),
  formatted: z.string().openapi({ example: '16.2%' }),
  total_customers: z.number().openapi({ example: 10127 }),
  attrited_count: z.number().openapi({ example: 1623 }),
});

const AttritedCountKpiSchema = z.object({
  value: z.number().openapi({ example: 1623 }),
  formatted: z.string().openapi({ example: '1,623' }),
  total_customers: z.number().openapi({ example: 10127 }),
});

const MedianSpendKpiSchema = z.object({
  value: z.number().openapi({ example: 250.5 }),
  formatted: z.string().openapi({ example: '$250.50' }),
  customer_count: z.number().openapi({ example: 10127 }),
});

const OverviewSchema = z.object({
  kpi_attrition_rate: AttritionRateKpiSchema,
  kpi_attrited_count: AttritedCountKpiSchema,
  kpi_median_monthly_spend: MedianSpendKpiSchema,
});

export const route = createRoute({
  method: 'get',
  path: '/kpis/overview',
  request: { query: QuerySchema },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: OverviewSchema,
        },
      },
      description: 'Return all header KPIs respecting global filters.',
    },
  },
});

export function register(app: OpenAPIHono) {
  app.openapi(route, async (c) => {
    const query = c.req.valid('query');
    const data = await loadCleanedData();
    const filters = parseKpiFilters(query as any); // Cast due to number vs string
    const filteredData = applyGlobalFilters(data, filters);
    const metrics = aggregateAttrition(filteredData);
    const monthlySpends = filteredData.map((row) => row.monthly_spend);
    const median = calculateMedian(monthlySpends);

    return c.json({
      kpi_attrition_rate: {
        value: metrics.attritionRate,
        formatted: formatPercentage(metrics.attritionRate),
        total_customers: metrics.totalCustomers,
        attrited_count: metrics.attritedCount,
      },
      kpi_attrited_count: {
        value: metrics.attritedCount,
        formatted: formatInteger(metrics.attritedCount),
        total_customers: metrics.totalCustomers,
      },
      kpi_median_monthly_spend: {
        value: median,
        formatted: formatCurrency(median),
        customer_count: filteredData.length,
      },
    });
  });
}
