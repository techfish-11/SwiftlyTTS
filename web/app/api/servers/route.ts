import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { randomUUID } from "crypto";
import fs from "fs/promises";
import path from "path";

// ジョブ管理ディレクトリ
const JOB_DIR = "/tmp/servers_jobs";

// ジョブ状態型
type JobStatus = "pending" | "done" | "error";
type JobData =
  | { status: "pending"; created: number }
  | { status: "done"; servers: { id: string; name: string }[]; created: number }
  | { status: "error"; error: string; created: number };

// ジョブファイルのパス
function jobFile(jobId: string): string {
  return path.join(JOB_DIR, `${jobId}.json`);
}

// ジョブ状態を保存
async function saveJob(jobId: string, data: JobData): Promise<void> {
  await fs.mkdir(JOB_DIR, { recursive: true });
  await fs.writeFile(jobFile(jobId), JSON.stringify(data), "utf8");
}

// ジョブ状態を取得
async function loadJob(jobId: string): Promise<JobData | null> {
  try {
    const data = await fs.readFile(jobFile(jobId), "utf8");
    return JSON.parse(data) as JobData;
  } catch {
    return null;
  }
}

// Discord APIからギルド一覧取得
async function fetchGuildsFromDiscord(
  accessToken: string
): Promise<{ servers: { id: string; name: string }[]; error?: string }> {
  let res;
  let lastError = null;
  for (let i = 0; i < 1; i++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);
    try {
      res = await fetch("https://discord.com/api/v10/users/@me/guilds", {
        headers: { Authorization: `Bearer ${accessToken}` },
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (res.ok) break;
      lastError = await res.text();
    } catch (e) {
      clearTimeout(timeoutId);
      lastError = (e instanceof Error ? e.message : String(e));
    }
    await new Promise(r => setTimeout(r, 500));
  }
  if (!res || !res.ok) {
    return { servers: [], error: "ギルド一覧の取得に失敗しました。Discord APIエラー: " + lastError };
  }
  let guilds: unknown = [];
  try {
    guilds = await res.json();
  } catch (e) {
    return { servers: [], error: "ギルド一覧の取得に失敗しました（JSONパースエラー）: " + (e instanceof Error ? e.message : String(e)) };
  }
  const servers = Array.isArray(guilds)
    ? guilds.map((g) => ({ id: (g as {id:string}).id, name: (g as {name:string}).name }))
    : [];
  return { servers };
}

// APIエントリポイント
export async function GET(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session || !session.accessToken) {
    return NextResponse.json({ error: "Discord認証情報がありません。再ログインしてください。" }, { status: 401 });
  }

  const url = new URL(request.url);
  const force = url.searchParams.get("force") === "1";
  const jobId = url.searchParams.get("job_id");

  // ポーリング: job_id指定時はジョブ状態を返す
  if (jobId) {
    const job = await loadJob(jobId);
    if (!job) {
      return NextResponse.json({ status: "not_found", error: "ジョブが見つかりません" }, { status: 404 });
    }
    // 完了時はサーバーリストも返す
    if (job.status === "done") {
      // クッキーをセット
      const cacheValue = encodeURIComponent(JSON.stringify({
        servers: job.servers,
        timestamp: job.created,
      }));
      const res = NextResponse.json({ status: "done", servers: job.servers });
      res.headers.set(
        "Set-Cookie",
        `guilds_cache=${cacheValue}; Path=/; Max-Age=300; SameSite=Lax`
      );
      return res;
    }
    if (job.status === "error") {
      return NextResponse.json({ status: "error", error: job.error }, { status: 500 });
    }
    return NextResponse.json({ status: job.status });
  }

  // クエリパラメータでforce=1なら強制再取得
  // Cookieからキャッシュ取得
  let cachedServers: unknown = null;
  let cacheTimestamp = 0;
  const cookieStr = request.headers.get("cookie") || "";
  const match = cookieStr.match(/guilds_cache=([^;]+)/);
  let cacheValid = false;
  if (match) {
    try {
      const cacheObj = JSON.parse(decodeURIComponent(match[1]));
      cachedServers = cacheObj.servers;
      cacheTimestamp = cacheObj.timestamp || 0;
      if (
        Array.isArray(cachedServers) &&
        typeof cacheTimestamp === "number" &&
        Date.now() - cacheTimestamp < 5 * 60 * 1000
      ) {
        cacheValid = true;
      }
    } catch {
      cacheValid = false;
    }
  }
  if (cacheValid && !force) {
    return NextResponse.json({ servers: cachedServers });
  }

  // 新規ジョブ発行
  const newJobId = randomUUID();
  // ジョブ初期状態を保存
  await saveJob(newJobId, { status: "pending", created: Date.now() });

  // バックグラウンドでDiscord API取得
  (async () => {
    const result = await fetchGuildsFromDiscord(session.accessToken as string);
    if (result.error) {
      await saveJob(newJobId, {
        status: "error",
        error: result.error,
        created: Date.now(),
      });
      return;
    }
    // Cookieキャッシュも更新
    await saveJob(newJobId, {
      status: "done",
      servers: result.servers,
      created: Date.now(),
    });
    // クッキー保存
    // クッキー値はJSONをエンコード
    const cacheValue = encodeURIComponent(JSON.stringify({
      servers: result.servers,
      timestamp: Date.now(),
    }));
    // サーバー側でレスポンスにクッキーをセット
    // ただしAPI Routeのバックグラウンド処理なので、クッキーはdone時に返す必要あり
    // → job_id指定時のdoneレスポンスでクッキーを返す
  })();

  // 即時レスポンス: job_idを返す
  return NextResponse.json({ status: "pending", job_id: newJobId });
}
