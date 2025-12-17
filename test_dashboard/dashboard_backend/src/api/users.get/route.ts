// src/api/routes/users.get/route.ts
import { z, createRoute } from "@hono/zod-openapi";

const ParamsSchema = z.object({
  id: z.string().min(3).openapi({
    param: { name: "id", in: "path" },
    example: "1212121",
  }),
});

const UserSchema = z.object({
  id: z.string().openapi({ example: "123" }),
  name: z.string().openapi({ example: "John Doe" }),
  age: z.number().openapi({ example: 42 }),
}).openapi("User");

export const route = createRoute({
  method: "get",
  path: "/users/{id}",
  request: { params: ParamsSchema },
  responses: {
    200: {
      content: { "application/json": { schema: UserSchema } },
      description: "Retrieve the user",
    },
  },
});

export function register(app: any) {
  // ✅ registering here both:
  // 1) runtime validation (c.req.valid('param'))
  // 2) OpenAPI registry entry
  app.openapi(route, (c: any) => {
    const { id } = c.req.valid("param");
    return c.json({ id, name: "Ultra-man", age: 20 }, 200);
  });
}