import type { Metadata } from "next";
import { GalleryView } from "@/components/gallery-view";
import { getGalleryPayload } from "@/lib/api";

type GalleryPageProps = {
  searchParams: Promise<{
    focus?: string;
  }>;
};

export const metadata: Metadata = {
  title: "Gallery",
};

export default async function GalleryPage({ searchParams }: GalleryPageProps) {
  const { focus } = await searchParams;
  const data = await getGalleryPayload(focus);

  return <GalleryView albums={data.albums} isFocused={data.is_focused} />;
}
