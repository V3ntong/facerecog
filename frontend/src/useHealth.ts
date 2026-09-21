import { useState, useEffect } from "react";
import { getHealth } from "./api";
import type { HealthResponse } from "./types";

export default function useHealth() {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => {});
  }, []);

  return health;
}
