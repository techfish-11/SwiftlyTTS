// Discord APIで所属ギルド一覧取得（rate limit対応）
async function fetchGuildsWithRetry(accessToken: string): Promise<DiscordGuild[] | {error: string}> {
  let lastError = null;
  for (let i = 0; i < 2; i++) {
    const res = await fetch("https://discord.com/api/v10/users/@me/guilds", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (res.status === 429) {
      // レートリミット
      try {
        const data = await res.json();
        const retry = typeof data.retry_after === "number" ? data.retry_after : 1;
        lastError = data.message || "Rate limited";
        await new Promise(r => setTimeout(r, Math.ceil(retry * 1000)));
        continue;
      } catch {
        lastError = "Rate limited (parse error)";
        await new Promise(r => setTimeout(r, 1000));
        continue;
      }
    }
    if (res.ok) {
      try {
        return await res.json();
      } catch {
        lastError = "Discord APIレスポンスのパースに失敗しました";
        break;
      }
    } else {
      try {
        lastError = await res.text();
      } catch {}
      break;
    }
  }
  return { error: `ギルド一覧の取得に失敗しました。Discord APIエラー: ${lastError || "不明"}` };
}
import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { Pool } from "pg";

type DiscordGuild = {
  id: string;
};

// DB接続設定（.envから取得）
const pool = new Pool({
  host: process.env.DB_HOST,
  port: Number(process.env.DB_PORT || 5432),
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
});

// GET: 所属ギルドの辞書一覧取得（?guild_id=xxx）
export async function GET(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session || !session.accessToken) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const url = new URL(req.url);
  const guildId = url.searchParams.get("guild_id");
  if (!guildId) {
    return NextResponse.json({ error: "guild_id required" }, { status: 400 });
  }
  // Discord APIで所属ギルド一覧取得（rate limit対応）
  const guilds = await fetchGuildsWithRetry(session.accessToken);
  if ("error" in guilds) {
    return NextResponse.json({ error: guilds.error }, { status: 500 });
  }
  const found = guilds.some((g: DiscordGuild) => g.id === guildId);
  if (!found) {
    return NextResponse.json({ error: "Forbidden: not a member of this guild" }, { status: 403 });
  }
  const { rows } = await pool.query(
    "SELECT key, value FROM dictionarynew WHERE guild_id = $1",
    [guildId]
  );
  return NextResponse.json({ dictionary: rows });
}

// POST: ギルド辞書エントリ追加/更新
export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session || !session.accessToken || !session.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const { guild_id, key, value } = await req.json();
  if (!guild_id || !key || typeof value !== "string") {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 });
  }
  // Discord APIで所属ギルド一覧取得（rate limit対応）
  const guilds = await fetchGuildsWithRetry(session.accessToken);
  if ("error" in guilds) {
    return NextResponse.json({ error: guilds.error }, { status: 500 });
  }
  const found = guilds.some((g: DiscordGuild) => g.id === guild_id);
  if (!found) {
    return NextResponse.json({ error: "Forbidden: not a member of this guild" }, { status: 403 });
  }
  await pool.query(
    `INSERT INTO dictionarynew (guild_id, key, value, author_id) VALUES ($1, $2, $3, $4)
     ON CONFLICT (guild_id, key) DO UPDATE SET value = $3, author_id = $4`,
    [guild_id, key, value, session.user.id]
  );
  // ボット側HTTPサーバーに通知（失敗しても無視）
  fetch(process.env.BOT_HTTP_URL + "/guild-dictionary/notify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ guild_id }),
  }).catch(() => {});
  return NextResponse.json({ ok: true });
}

// DELETE: ギルド辞書エントリ削除
export async function DELETE(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session || !session.accessToken) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const { guild_id, key } = await req.json();
  if (!guild_id || !key) {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 });
  }
  // Discord APIで所属ギルド一覧取得（rate limit対応）
  const guilds = await fetchGuildsWithRetry(session.accessToken);
  if ("error" in guilds) {
    return NextResponse.json({ error: guilds.error }, { status: 500 });
  }
  const found = guilds.some((g: DiscordGuild) => g.id === guild_id);
  if (!found) {
    return NextResponse.json({ error: "Forbidden: not a member of this guild" }, { status: 403 });
  }
  await pool.query(
    "DELETE FROM dictionarynew WHERE guild_id = $1 AND key = $2",
    [guild_id, key]
  );
  // ボット側HTTPサーバーに通知（失敗しても無視）
  fetch(process.env.BOT_HTTP_URL + "/guild-dictionary/notify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ guild_id }),
  }).catch(() => {});
  return NextResponse.json({ ok: true });
}
