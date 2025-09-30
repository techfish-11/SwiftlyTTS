import { NextResponse } from 'next/server';

// Prometheus range query proxy endpoint
// Expects query params: query (PromQL), start (unix seconds), end (unix seconds), step (seconds)
// The Prometheus server base URL must be set in environment variable PROMETHEUS_URL

const PROMETHEUS_URL = process.env.PROMETHEUS_URL;

function ensureScheme(u?: string | null) {
  if (!u) return null;
  if (/^https?:\/\//i.test(u)) return u;
  return `http://${u}`; // default to http if scheme missing
}

const NORMALIZED_PROM_URL = ensureScheme(PROMETHEUS_URL);

export async function GET(req: Request) {
  if (!PROMETHEUS_URL || !NORMALIZED_PROM_URL) {
    return NextResponse.json(
      { error: 'PROMETHEUS_URL not configured or invalid (set to host[:port] or http(s)://host[:port])' },
      { status: 500 }
    );
  }

  const { searchParams } = new URL(req.url);
  const query = searchParams.get('query') || 'bot_server_count';
  const start = searchParams.get('start');
  const end = searchParams.get('end');
  const step = searchParams.get('step') || '2419';

  if (!start || !end) {
    return NextResponse.json({ error: 'start and end query params are required (unix seconds)' }, { status: 400 });
  }

  // Build Prometheus query_range URL using URL API for robustness
  let target: string;
  try {
    const base = new URL(NORMALIZED_PROM_URL);
    const url = new URL('/api/v1/query_range', base);
    url.searchParams.set('query', query);
    url.searchParams.set('start', String(start));
    url.searchParams.set('end', String(end));
    url.searchParams.set('step', String(step));
    target = url.toString();
  } catch (err) {
    return NextResponse.json({ error: 'Failed to build Prometheus URL', detail: String(err) }, { status: 500 });
  }

  try {
    const upstreamRes = await fetch(target, { cache: 'no-store' });
    const data = await upstreamRes.json();

    // Forward response but avoid sending upstream security headers
    const headers = new Headers();
    headers.set('content-type', 'application/json');
    headers.set('x-proxied-by', 'SwiftlyTTS-prometheus-proxy');

    return new Response(JSON.stringify(data), { status: upstreamRes.status, headers });
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: 'Failed to query Prometheus', detail }, { status: 502 });
  }
}
