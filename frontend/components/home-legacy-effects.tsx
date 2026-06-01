"use client";

import { useEffect } from "react";
import { initHomeLightfield } from "@/components/home-lightfield";
import { initHomeLiquidGlass } from "@/components/home-liquid-glass";

export function HomeLegacyEffects() {
  useEffect(() => {
    const cleanupLightfield = initHomeLightfield();
    const cleanupLiquidGlass = initHomeLiquidGlass();

    return () => {
      cleanupLiquidGlass();
      cleanupLightfield();
    };
  }, []);

  return null;
}
