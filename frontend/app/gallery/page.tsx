import type { Metadata } from "next";
import { GalleryView } from "@/components/gallery-view";
import { getGalleryPayload } from "@/lib/api";

type GalleryPageProps = {
  searchParams: Promise<{
    focus?: string;
  }>;
};

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "Gallery",
  description: "Photo gallery by Yixun Hong. Cycling, hiking, and travel photography.",
};

export default async function GalleryPage({ searchParams }: GalleryPageProps) {
  const { focus } = await searchParams;
  const data = await getGalleryPayload(focus);

  return <GalleryView albums={data.albums} isFocused={data.is_focused} />;
}
