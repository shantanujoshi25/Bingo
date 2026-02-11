import type { LobbyInfo } from '../types';
import { BUY_IN_AMOUNT } from '../config';

interface Props {
  lobbies: LobbyInfo[];
  onSelectLobby: (lobbyId: string) => void;
  isJoining: boolean;
}

export default function LobbyList({ lobbies, onSelectLobby, isJoining }: Props) {
  return (
    <div className="flex flex-col items-center min-h-[100dvh] px-4 py-6">
      <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-b from-white to-gray-400 bg-clip-text text-transparent mb-1">
        Bingo with Aliens
      </h1>
      <p className="text-gray-500 text-xs mb-6">
        Buy-in: {BUY_IN_AMOUNT.toLocaleString()} coins
      </p>

      <h2 className="text-gray-400 text-xs font-medium mb-3 uppercase tracking-wide self-start max-w-sm w-full mx-auto">
        Available Lobbies
      </h2>

      <div className="w-full max-w-sm space-y-3">
        {lobbies.map((lobby) => {
          const isFull = lobby.player_count >= lobby.max_players;
          const isActive = lobby.status === 'active';
          const canJoin = !isFull && !isActive;

          return (
            <div
              key={lobby.lobby_id}
              className="bg-gray-800/60 border border-gray-700/50 rounded-xl px-4 py-3 flex items-center justify-between"
            >
              <div className="min-w-0">
                <p className="text-white font-bold text-base truncate">
                  {lobby.name}
                </p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-gray-400 text-xs">
                    {lobby.player_count}/{lobby.max_players} players
                  </span>
                  <span className="text-yellow-500/80 text-xs font-medium">
                    {lobby.pot.toLocaleString()} coins
                  </span>
                  {isActive && (
                    <span className="text-orange-400 text-[10px] font-medium uppercase">
                      In Progress
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={() => onSelectLobby(lobby.lobby_id)}
                disabled={!canJoin || isJoining}
                className="ml-3 px-4 py-2 bg-blue-600 active:bg-blue-700 disabled:opacity-40 disabled:bg-gray-700 rounded-xl font-bold text-sm transition-all active:scale-[0.98] touch-manipulation shrink-0"
              >
                {isActive ? 'Playing' : isFull ? 'Full' : 'Join'}
              </button>
            </div>
          );
        })}

        {lobbies.length === 0 && (
          <p className="text-gray-600 text-sm text-center py-8">
            No lobbies available. One will appear shortly...
          </p>
        )}
      </div>
    </div>
  );
}
