// src/api/app.ts
import { OpenAPIHono } from "@hono/zod-openapi";
import { swaggerUI } from "@hono/swagger-ui";
import { discoverRouteModules } from "./spec/discover.js";
import { serve } from '@hono/node-server'

export async function createApp() {
  const app = new OpenAPIHono({
    // optional: central validation error formatting
    defaultHook: (result, c) => {
      if (!result.success) return c.json({ error: "Validation error" }, 422);
    },
  });

  const mods = await discoverRouteModules();
  for (const m of mods) m.register(app);

  // OpenAPI JSON endpoint
  app.doc("/doc", {
    openapi: "3.0.0",
    info: { title: "My API", version: "1.0.0" },
  }); // :contentReference[oaicite:4]{index=4}

  // Swagger UI
  app.get("/ui", swaggerUI({ url: "/doc" })); // :contentReference[oaicite:5]{index=5}

  return app;
}
const app = await createApp();

serve({
  fetch: app.fetch,
  port: Number(process.env.PORT ?? 8787),
});

console.log(`✅ Server running on http://localhost:${process.env.PORT ?? 8787}`);
console.log(`📄 OpenAPI JSON: http://localhost:${process.env.PORT ?? 8787}/doc`);
console.log(`🧭 Swagger UI:   http://localhost:${process.env.PORT ?? 8787}/ui`);