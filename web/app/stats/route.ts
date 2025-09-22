import { type NextRequest } from 'next/server';

export function GET(request: NextRequest) {
    const url = new URL('https://stats.sakana11.org/public-dashboards/68f9b3d55f43490c9d07c1daf1475f3c', request.nextUrl.origin);
    return Response.redirect(url.toString(), 302);
}

export function POST(request: NextRequest) {
    const url = new URL('https://stats.sakana11.org/public-dashboards/68f9b3d55f43490c9d07c1daf1475f3c', request.nextUrl.origin);
    return Response.redirect(url.toString(), 302);
}