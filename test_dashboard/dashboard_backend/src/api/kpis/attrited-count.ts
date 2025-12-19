import { z, createRoute, OpenAPIHono } from '@hono/zod-openapi';
import { loadCleanedData } from '../../utils/cleaned_data_loader.js';
import type { CleanedDataRow } from '../../utils/cleaned_data_loader.js';
import { parseKpiFilters } from '../../utils/filter_parser.js';
import { applyGlobalFilters } from '../../utils/filter_applicator.js';
import { aggregateAttrition } from '../../utils/attrition_aggregations.js';
import { formatInteger } from '../../utils/formatters.js';

const QuerySchema = z.object({
  incomeCategories: z.string().openapi({ param: { name: 'incomeCategories', in: 'query', required: false } }),
  cardCategories: z.string().openapi({ param: { name: 'cardCategories', in: 'query', required: false } }),
  spendQuintiles: z.string().openapi({ param: { name: 'spendQuintiles', in: 'query', required: false } }),
  tenureMin: z.coerce.number().openapi({ param: { name: 'tenureMin', in: 'query', required: false } }).optional(),
  tenureMax: z.coerce.number().openapi({ param: { name: 'tenureMax', in: 'query', required: false } }).optional(),
});

const AttritedCountSchema = z.object({
  value: z.number().openapi({ example: 1623 }),
  formatted: z.string().openapi({ example: '1,623' }),
  total_customers: z.number().openapi({ example: 10127 }),
});

export const route = createRoute({
  method: 'get',
  path: '/kpis/attrited-count',
  request: { query: QuerySchema },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: AttritedCountSchema,
        },
      },
      description: 'Attrited customers count KPI with filters.',
    },
  },
});

export function register(app: OpenAPIHono) {
  app.openapi(route, async (c) => {
    const query = c.req.valid('query');
    const data = await loadCleanedData();
    const filters = parseKpiFilters(query as any);
    const filteredData = applyGlobalFilters(data, filters);
    const metrics = aggregateAttrition(filteredData);

    return c.json({
      value: metrics.attritedCount,
      formatted: formatInteger(metrics.attritedCount),
      total_customers: metrics.totalCustomers,
    });
  });
}
