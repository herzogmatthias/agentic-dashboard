// src/spec/discover.ts
import fg from "fast-glob";
import path from "node:path";
import { pathToFileURL } from "node:url";

export async function discoverRouteModules() {
  const files = await fg("src/api/**/route.ts");
  const modules: any[] = [];

  for (const f of files) {
    const mod = await import(pathToFileURL(path.resolve(f)).href);
    if (!mod.route || !mod.register) {
      throw new Error(`Invalid route module: ${f} (must export route + register)`);
    }
    modules.push(mod);
  }
  return modules;
}