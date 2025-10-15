import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { Pool } from "pg";

// DB接続設定（.envから取得）
const pool = new Pool({
  host: process.env.DB_HOST,
  port: Number(process.env.DB_PORT || 5432),
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
});

// GET: ユーザー辞書一覧取得
export async function GET(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session || !session.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const userId = session.user.id;
  const { rows } = await pool.query(
    "SELECT key, value FROM user_dictionary WHERE user_id = $1",
    [userId]
  );
  return NextResponse.json({ dictionary: rows });
}

// POST: 辞書エントリ追加/更新
export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session || !session.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const userId = session.user.id;
  const { key, value } = await req.json();
  if (!key || typeof value !== "string") {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 });
  }
  await pool.query(
    `INSERT INTO user_dictionary (user_id, key, value) VALUES ($1, $2, $3)
     ON CONFLICT (user_id, key) DO UPDATE SET value = $3`,
    [userId, key, value]
  );
  // ボット側HTTPサーバーに通知（失敗しても無視）
  fetch(process.env.BOT_HTTP_URL + "/user-dictionary/notify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId }),
  }).catch(() => {});
  return NextResponse.json({ ok: true });
}

// DELETE: 辞書エントリ削除
export async function DELETE(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session || !session.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const userId = session.user.id;
  const { key } = await req.json();
  if (!key) {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 });
  }
  await pool.query(
    "DELETE FROM user_dictionary WHERE user_id = $1 AND key = $2",
    [userId, key]
  );
  // ボット側HTTPサーバーに通知（失敗しても無視）
  fetch(process.env.BOT_HTTP_URL + "/user-dictionary/notify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId }),
  }).catch(() => {});
  return NextResponse.json({ ok: true });
}
