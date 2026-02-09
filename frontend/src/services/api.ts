import { API_URL } from '../config';
import type { GameStatus, JoinLobbyResponse, ClaimResult } from '../types';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail));
  }

  return res.json();
}

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

export async function joinLobby(
  token: string,
  alienId: string
): Promise<JoinLobbyResponse> {
  return request('/api/game/join', {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ alien_id: alienId }),
  });
}

export async function submitGrid(
  token: string,
  lobbyId: string,
  alienId: string,
  grid: number[][]
): Promise<{ success: boolean; ready_count: number; message: string }> {
  return request(`/api/game/${lobbyId}/submit-grid`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ alien_id: alienId, grid }),
  });
}

export async function getGameStatus(
  token: string,
  lobbyId: string
): Promise<GameStatus> {
  return request(`/api/game/${lobbyId}/status`, {
    headers: authHeaders(token),
  });
}

export async function claimBingo(
  token: string,
  lobbyId: string,
  alienId: string,
  highlightedNumbers: number[]
): Promise<ClaimResult> {
  return request(`/api/game/${lobbyId}/claim`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ alien_id: alienId, highlighted_numbers: highlightedNumbers }),
  });
}
