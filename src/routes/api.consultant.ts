import { createFileRoute } from "@tanstack/react-router";
import type {} from "@tanstack/react-start";
import { createConsultantHandlers } from "@/consultant/handler.server";

let handlers: ReturnType<typeof createConsultantHandlers> | undefined;

function getHandlers() {
  handlers ??= createConsultantHandlers();
  return handlers;
}

export const Route = createFileRoute("/api/consultant")({
  server: {
    handlers: {
      GET: () => getHandlers().GET(),
      POST: ({ request }) => getHandlers().POST(request),
    },
  },
});
