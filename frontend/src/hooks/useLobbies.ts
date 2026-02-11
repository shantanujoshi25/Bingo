import { useState, useEffect, useCallback } from 'react';
import { listLobbies } from '../services/api';
import type { LobbyInfo } from '../types';

const LOBBIES_POLL_INTERVAL = 3000;

export function useLobbies(authToken: string | null, enabled: boolean) {
  const [lobbies, setLobbies] = useState<LobbyInfo[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchLobbies = useCallback(async () => {
    if (!authToken) return;
    try {
      const data = await listLobbies(authToken);
      setLobbies(data.lobbies);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch lobbies');
    }
  }, [authToken]);

  useEffect(() => {
    if (!authToken || !enabled) return;
    fetchLobbies();
    const interval = setInterval(fetchLobbies, LOBBIES_POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [authToken, enabled, fetchLobbies]);

  return { lobbies, error, refetch: fetchLobbies };
}
