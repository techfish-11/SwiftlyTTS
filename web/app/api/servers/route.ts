
import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";

// Discord APIから所属ギルド一覧を取得
export async function GET(request: Request) {

  const session = await getServerSession(authOptions);
  if (!session || !session.accessToken) {
    return NextResponse.json({ error: "Discord認証情報がありません。再ログインしてください。" }, { status: 401 });
  }

  // クエリパラメータでforce=1なら強制再取得
  // (urlは不要なので削除)
  let force = false;
  try {
    // Next.js API Routeではreq.urlが使えないので、headers.refererからクエリを取得
    const referer = (typeof window === "undefined" ? undefined : window.location.href) || "";
    force = referer.includes("force=1");
  } catch {}

  // Cookieからキャッシュ取得

  let cachedServers: unknown = null;
  let cacheTimestamp = 0;
  // サーバーサイド: request.headersからCookie取得
  const cookieStr = request.headers.get("cookie") || "";
  const match = cookieStr.match(/guilds_cache=([^;]+)/);
  let cacheValid = false;
  if (match) {
    try {
      const cacheObj = JSON.parse(decodeURIComponent(match[1]));
      cachedServers = cacheObj.servers;
      cacheTimestamp = cacheObj.timestamp || 0;
      // 内容が正しいか判定（serversが配列、timestampが数値、5分以内）
      if (Array.isArray(cachedServers) && typeof cacheTimestamp === "number" && (Date.now() - cacheTimestamp < 5 * 60 * 1000)) {
        cacheValid = true;
      }
    } catch {
      cacheValid = false;
    }
  }

  // クッキーが有効ならAPIは一切叩かずクッキーのみ返す
  if (cacheValid && !force) {
    return NextResponse.json({ servers: cachedServers });
  }

  // Discord API: /users/@me/guilds
  let res;
  let lastError = null;
  for (let i = 0; i < 2; i++) { // 2回までリトライ
    try {
      res = await fetch("https://discord.com/api/v10/users/@me/guilds", {
        headers: {
          Authorization: `Bearer ${session.accessToken}`,
        },
      });
      if (res.ok) break;
      lastError = await res.text();
    } catch (e) {
      lastError = (e instanceof Error ? e.message : String(e));
    }
    await new Promise(r => setTimeout(r, 500)); // 0.5秒待機
  }

  if (!res || !res.ok) {
    // Discord APIのエラー内容を返す
    return NextResponse.json({ error: "ギルド一覧の取得に失敗しました。Discord APIエラー: " + lastError }, { status: 500 });
  }
  let guilds: unknown = [];
  try {
    guilds = await res.json();
  } catch (e) {
    return NextResponse.json({ error: "ギルド一覧の取得に失敗しました（JSONパースエラー）: " + (e instanceof Error ? e.message : String(e)) }, { status: 500 });
  }
  // 必要な情報だけ返す
  const servers = Array.isArray(guilds)
    ? guilds.map((g) => ({ id: (g as {id:string}).id, name: (g as {name:string}).name }))
    : [];

  // Cookieにキャッシュ保存（5分有効）
  const cacheObj = { servers, timestamp: Date.now() };
  const cookie = `guilds_cache=${encodeURIComponent(JSON.stringify(cacheObj))}; Path=/; Max-Age=300; SameSite=Lax`;
  const response = NextResponse.json({ servers });
  response.headers.set("Set-Cookie", cookie);
  return response;
}
