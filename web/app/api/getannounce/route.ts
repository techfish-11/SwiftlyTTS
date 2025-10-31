import { NextResponse } from 'next/server';
import { Pool } from 'pg';

export async function GET() {
  const pool = new Pool({
    host: process.env.DB_HOST,
    port: process.env.DB_PORT ? Number(process.env.DB_PORT) : 5432,
    database: process.env.DB_NAME,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
  });

  try {
    const client = await pool.connect();
    try {
      const res = await client.query(
        'SELECT announce, updated_at FROM announce_config WHERE id = $1 LIMIT 1',
        [1]
      );
      const announce = res.rows[0]?.announce ?? '';
      const updated_at = res.rows[0]?.updated_at ?? null;
      return NextResponse.json({ announce, updated_at });
    } finally {
      client.release();
    }
  } catch (e) {
    console.error('Error in GET /api/getannounce:', e);
    return NextResponse.json({ announce: '', updated_at: null }, { status: 500 });
  } finally {
    await pool.end();
  }
}
