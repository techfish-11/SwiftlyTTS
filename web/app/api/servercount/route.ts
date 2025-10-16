import { NextResponse } from "next/server";

export async function GET() {
  // Prefer local bot HTTP server. This server should be running alongside the bot.
  // If you run the bot_http_server on a different host/port, update this URL or make it env-driven.
  const BOT_HTTP = process.env.BOT_HTTP_URL || "http://127.0.0.1:8000";

  const res = await fetch(`${BOT_HTTP}/servers`, { cache: "no-store" });
  if (!res.ok) {
    // Return a helpful JSON error to the client
    const text = await res.text();
    return NextResponse.json({ ok: false, status: res.status, message: text }, { status: 502 });
  }
  const data = await res.json();
  return NextResponse.json(data);
}