export function applyFilters(rows, filter) {
    return rows.filter((r) => {
        if (filter.incomeCategories && filter.incomeCategories.length > 0) {
            if (!r.Income_Category || !filter.incomeCategories.includes(r.Income_Category))
                return false;
        }
        if (filter.cardCategories && filter.cardCategories.length > 0) {
            if (!r.Card_Category || !filter.cardCategories.includes(r.Card_Category))
                return false;
        }
        if (filter.spendQuintiles && filter.spendQuintiles.length > 0) {
            if (typeof r.spend_quintile !== 'number' || !filter.spendQuintiles.includes(r.spend_quintile))
                return false;
        }
        if (filter.tenureMonths) {
            const min = filter.tenureMonths.min ?? Number.NEGATIVE_INFINITY;
            const max = filter.tenureMonths.max ?? Number.POSITIVE_INFINITY;
            const tenure = r.tenure_months ?? r.Months_on_book ?? 0;
            if (Number.isNaN(tenure))
                return false;
            if (tenure < min || tenure > max)
                return false;
        }
        return true;
    });
}
