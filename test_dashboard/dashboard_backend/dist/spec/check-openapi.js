// src/spec/check-openapi.ts
import fs from "node:fs";
import { discoverRouteModules } from "./discover.js";
export async function checkOpenAPICompleteness() {
    const mods = await discoverRouteModules();
    const expected = new Set(mods.map(m => m.route.operationId ?? m.route?.getRoutingPath?.() ?? null));
    const doc = JSON.parse(fs.readFileSync("artifacts/spec/openapi.json", "utf8"));
    const found = new Set();
    for (const [p, obj] of Object.entries(doc.paths ?? {})) {
        for (const [method, op] of Object.entries(obj)) {
            if (op?.operationId)
                found.add(op.operationId);
        }
    }
    const missing = [...expected].filter(x => x && !found.has(x));
    if (missing.length)
        throw new Error(`OpenAPI missing operationIds: ${missing.join(", ")}`);
}
