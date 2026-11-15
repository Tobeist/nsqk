import { askClaude, ChatError, claudeConfiguration, readChatRequest } from "../../../lib/claude-server";

export const runtime = "nodejs";
export const maxDuration = 180;

export async function GET() {
  return Response.json(claudeConfiguration(), { headers: { "Cache-Control": "no-store" } });
}

export async function POST(request: Request) {
  try {
    const input = await readChatRequest(request);
    return Response.json(await askClaude(input, request.signal), { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const status = error instanceof ChatError ? error.status : 500;
    return Response.json({ error: error instanceof ChatError ? error.message : "No se pudo completar la consulta. Intenta de nuevo." }, {
      status,
      headers: { "Cache-Control": "no-store", ...(status === 429 ? { "Retry-After": "60" } : {}) },
    });
  }
}
