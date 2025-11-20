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

// GET: ユーザーの声設定を取得
export async function GET(req: NextRequest) {
    const session = await getServerSession(authOptions);
    if (!session || !session.user?.id) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    const userId = session.user.id;
    const { rows } = await pool.query(
        "SELECT speaker_id FROM user_voice WHERE user_id = $1",
        [userId]
    );

    if (rows.length > 0) {
        return NextResponse.json({ speaker_id: rows[0].speaker_id });
    } else {
        return NextResponse.json({ speaker_id: null });
    }
}

// POST: ユーザーの声設定を更新
export async function POST(req: NextRequest) {
    const session = await getServerSession(authOptions);
    if (!session || !session.user?.id) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    const userId = session.user.id;
    const { speaker_id } = await req.json();

    if (speaker_id === null || speaker_id === undefined) {
        return NextResponse.json({ error: "Invalid speaker_id" }, { status: 400 });
    }

    await pool.query(
        `INSERT INTO user_voice (user_id, speaker_id) VALUES ($1, $2)
     ON CONFLICT (user_id) DO UPDATE SET speaker_id = $2`,
        [userId, String(speaker_id)]
    );

    // ボット側HTTPサーバーに通知（失敗しても無視）
    try {
        const botHttpUrl = process.env.BOT_HTTP_URL;
        if (botHttpUrl) {
            await fetch(`${botHttpUrl}/user-voice/notify`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: userId }),
            });
        }
    } catch (error) {
        console.error("Failed to notify bot about voice change:", error);
        // エラーは無視して続行
    }

    return NextResponse.json({ ok: true });
}
