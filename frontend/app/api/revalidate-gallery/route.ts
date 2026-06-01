import { revalidatePath, revalidateTag } from "next/cache";
import { NextResponse } from "next/server";

export async function POST() {
  revalidatePath("/gallery");
  revalidateTag("gallery", "default");
  return NextResponse.json({ revalidated: true });
}
