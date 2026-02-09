import { useState, useEffect, useCallback } from 'react';
import { getGameStatus } from '../services/api';
import { POLL_INTERVAL } from '../config';
import type { GameStatus } from '../types';

export function useGameState(lobbyId: string | null, authToken: string | null) {
  const [gameState, setGameState] = useState<GameStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!lobbyId || !authToken) return;
    try {
      const data = await getGameStatus(authToken, lobbyId);
      setGameState(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch game state');
    }
  }, [lobbyId, authToken]);

  useEffect(() => {
    if (!lobbyId || !authToken) return;

    // Fetch immediately
    fetchStatus();

    const interval = setInterval(fetchStatus, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [lobbyId, authToken, fetchStatus]);

  return { gameState, error, refetch: fetchStatus };
}
