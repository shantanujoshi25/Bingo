export interface Player {
  alien_id: string;
  numbers: number[];
  grid: number[][];
  ready: boolean;
  active: boolean;
  joined_at: string;
}

export interface GameStatus {
  lobby_id: string;
  status: 'forming' | 'active' | 'finished' | 'in_progress';
  buy_in_amount: number;
  pot: number;
  player_count: number;
  ready_count: number;
  players: Record<string, Player>;
  forming_deadline: string | null;
  latest_number: number | null;
  previous_number: number | null;
  called_numbers: number[];
  winner: string | null;
  time_elapsed: number;
}

export interface ClaimResult {
  valid: boolean;
  winner: boolean;
  kicked: boolean;
  pot?: number;
  message: string;
  pattern?: string;
}

export interface JoinLobbyResponse {
  lobby_id: string;
  status: string;
  player_count: number;
  pot: number;
}
