// Next.js route handler that invalidates the public /gallery page's
// 60-second ISR cache. Called by the upload manager after a star toggle
// so unstarred folders disappear from /gallery immediately, not after
// the cache window expires.
import { revalidatePath } from "next/cache";
import { NextResponse } from "next/server";

export async function POST() {
  revalidatePath("/gallery");
  return NextResponse.json({ revalidated: true });
}
