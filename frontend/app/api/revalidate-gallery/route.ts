import { revalidatePath } from "next/cache";
import { NextResponse } from "next/server";

export async function POST() {
  // Clear the Full Route Cache for /gallery, forcing a fresh render on next request.
  // This also signals the client-side Router Cache to invalidate for this path.
  revalidatePath("/gallery");
  return NextResponse.json({ revalidated: true, now: Date.now() });
}
