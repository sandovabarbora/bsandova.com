// api.bsandova.com → the sitewitness server on Fly. Nothing but a proxy: the agent, the rules, the
// limits and the trace live in the Python package. The Worker adds the real client address in a
// header the server is configured to trust (X-Client-IP, from CF-Connecting-IP) and CORS.

const UPSTREAM = "https://sitewitness-bsandova.fly.dev";

function corsHeaders(origin, env) {
  const allowed = (env.ALLOWED_ORIGINS || "").split(",").map((s) => s.trim());
  const o = allowed.includes(origin) ? origin : allowed[0];
  return { "Access-Control-Allow-Origin": o, "Access-Control-Allow-Methods": "POST, GET, OPTIONS", "Access-Control-Allow-Headers": "content-type, x-eval-key", "Vary": "Origin" };
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const cors = corsHeaders(origin, env);
    if (request.method === "OPTIONS") return new Response(null, { headers: cors });
    const url = new URL(request.url);
    if (!["/ask", "/health"].includes(url.pathname)) return new Response("POST /ask {question} · GET /health", { status: 404, headers: cors });
    const headers = new Headers({ "content-type": "application/json", "X-Client-IP": request.headers.get("CF-Connecting-IP") || "0" });
    const ek = request.headers.get("X-Eval-Key");
    if (ek) headers.set("X-Eval-Key", ek);
    let upstream;
    try {
      upstream = await fetch(UPSTREAM + url.pathname, { method: request.method, headers, body: request.method === "POST" ? await request.text() : undefined });
    } catch (e) {
      return Response.json({ error: "the assistant is unreachable" }, { status: 502, headers: cors });
    }
    const body = await upstream.text();
    return new Response(body, { status: upstream.status, headers: { ...cors, "content-type": upstream.headers.get("content-type") || "application/json" } });
  },
};
