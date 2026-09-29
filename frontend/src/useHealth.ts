import { useCallback, useEffect, useState } from "react";
import { getHealth } from "./api";
import type { HealthResponse } from "./types";

interface Health {
  health: HealthResponse | null;
  failed: boolean;
  refresh: () => void;
}

/** The desk's own records for the rail: prints on file, match gate, provider. */
export default function useHealth(): Health {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [failed, setFailed] = useState(false);

  const refresh = useCallback(() => {
    getHealth()
      .then((next) => {
        setHealth(next);
        setFailed(false);
      })
      .catch(() => setFailed(true));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { health, failed, refresh };
}
