import type { CleanedDataRow } from "./cleaned_data_loader.js";
import type { ParsedFilters } from "./filter_parser.js";

export function applyGlobalFilters(data: CleanedDataRow[], filters: ParsedFilters): CleanedDataRow[] {
  return data.filter((row) => {
    if (filters.incomeCategories && filters.incomeCategories.length) {
      if (!filters.incomeCategories.includes(row.Income_Category)) {
        return false;
      }
    }

    if (filters.cardCategories && filters.cardCategories.length) {
      if (!filters.cardCategories.includes(row.Card_Category)) {
        return false;
      }
    }

    if (filters.spendQuintiles && filters.spendQuintiles.length) {
      if (!filters.spendQuintiles.includes(row.spend_quintile)) {
        return false;
      }
    }

    if (filters.tenureRange) {
      const { min, max } = filters.tenureRange;
      if (row.tenure_months < min || row.tenure_months > max) {
        return false;
      }
    }

    return true;
  });
}
