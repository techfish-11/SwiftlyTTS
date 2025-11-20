import { NextRequest, NextResponse } from "next/server";

// ボット側のHTTP APIからボイスサンプルを取得
export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ speaker_id: string }> }
) {
    const { speaker_id: speakerId } = await params;

    if (!speakerId || isNaN(parseInt(speakerId))) {
        return NextResponse.json({ error: "Invalid speaker_id" }, { status: 400 });
    }

    try {
        const botHttpUrl = process.env.BOT_HTTP_URL;
        if (!botHttpUrl) {
            return NextResponse.json({ error: "BOT_HTTP_URL not configured" }, { status: 500 });
        }

        // ボット側のAPIを呼び出し
        const response = await fetch(`${botHttpUrl}/voice-sample/${speakerId}`, {
            method: "GET",
        });

        if (!response.ok) {
            throw new Error(`Bot API returned ${response.status}`);
        }

        // WAVデータを取得
        const audioBuffer = await response.arrayBuffer();

        // クライアントに返す
        return new NextResponse(audioBuffer, {
            status: 200,
            headers: {
                "Content-Type": "audio/wav",
                "Content-Disposition": `inline; filename=sample_${speakerId}.wav`,
                "Cache-Control": "public, max-age=86400", // 24時間キャッシュ
            },
        });
    } catch (error) {
        console.error(`Error fetching voice sample for speaker ${speakerId}:`, error);
        return NextResponse.json(
            { error: "Failed to fetch voice sample" },
            { status: 500 }
        );
    }
}
