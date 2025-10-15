import { NextResponse } from "next/server";

export async function GET() {
  const res = await fetch("https://techfish.dev/api/swiftlytts/servers", {
    cache: "no-store",
  });
  const data = await res.json();
  return NextResponse.json(data);
}