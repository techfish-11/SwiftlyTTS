import { NextResponse } from "next/server";
import fetch from "node-fetch";

export async function GET() {
  const BOT_HTTP = process.env.BOT_HTTP_URL || "http://127.0.0.1:8000";

  try {
    const res = await fetch(`${BOT_HTTP}/servers`);
    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json({ error: `Bot HTTPサーバーから取得失敗: ${text}` }, { status: res.status });
    }
    const data = (await res.json()) as { count?: number };
    // サーバー数を返す（data.countがなければ0）
    return NextResponse.json({ count: typeof data.count === "number" ? data.count : 0 });
  } catch {
    return NextResponse.json(
      { error: "Bot HTTPサーバーに接続できません。FastAPIが起動しているか確認してください。" },
      { status: 500 }
    );
  }
}