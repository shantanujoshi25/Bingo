import { useState, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useGameState } from '../hooks/useGameState';
import { joinLobby, submitGrid, claimBingo } from '../services/api';
import LoadingSpinner from './LoadingSpinner';
import Lobby from './Lobby';
import BingoCard from './BingoCard';
import NumberDisplay from './NumberDisplay';
import ClaimButton from './ClaimButton';
import GameChat from './GameChat';
import WinnerScreen from './WinnerScreen';
import KickedScreen from './KickedScreen';

type Phase = 'lobby' | 'playing';
type Overlay = 'won' | 'kicked' | 'finished' | null;

export default function GameFlow() {
  const { authToken, alienId, isReady } = useAuth();

  const [lobbyId, setLobbyId] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>('lobby');
  const [overlay, setOverlay] = useState<Overlay>(null);
  const [playerGrid, setPlayerGrid] = useState<number[][]>([]);
  const [markedNumbers, setMarkedNumbers] = useState<Set<number>>(new Set());
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [kickMessage, setKickMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { gameState } = useGameState(lobbyId, authToken);

  // Sync phase from server state
  const syncPhaseFromServer = useCallback(() => {
    if (!gameState || overlay) return;

    if (gameState.status === 'active' && phase !== 'playing') {
      setPhase('playing');
    } else if (gameState.status === 'finished' && phase === 'playing') {
      setOverlay('finished');
    }
  }, [gameState, phase, overlay]);

  if (gameState) {
    syncPhaseFromServer();
  }

  const handleJoin = async () => {
    if (!authToken || !alienId) return;
    setIsLoading(true);
    setError(null);
    try {
      const result = await joinLobby(authToken, alienId);
      setLobbyId(result.lobby_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to join lobby');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitGrid = async (grid: number[][]) => {
    if (!authToken || !alienId || !lobbyId) return;
    setIsLoading(true);
    setError(null);
    try {
      await submitGrid(authToken, lobbyId, alienId, grid);
      setPlayerGrid(grid);
      setHasSubmitted(true);
      setMarkedNumbers(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit grid');
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleMark = (num: number) => {
    setMarkedNumbers((prev) => {
      const next = new Set(prev);
      if (next.has(num)) {
        next.delete(num);
      } else {
        next.add(num);
      }
      return next;
    });
  };

  const handleClaim = async () => {
    if (!authToken || !alienId || !lobbyId) return;
    setIsLoading(true);
    setError(null);
    try {
      const result = await claimBingo(authToken, lobbyId, alienId, Array.from(markedNumbers));
      if (result.valid && result.winner) {
        setOverlay('won');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Claim failed';
      try {
        const parsed = JSON.parse(msg);
        if (parsed.kicked) {
          setKickMessage(parsed.message || 'Invalid claim. You have been removed.');
          setOverlay('kicked');
          return;
        }
      } catch {
        // Not JSON
      }
      setKickMessage(msg);
      setOverlay('kicked');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePlayAgain = () => {
    setLobbyId(null);
    setPhase('lobby');
    setOverlay(null);
    setPlayerGrid([]);
    setMarkedNumbers(new Set());
    setHasSubmitted(false);
    setKickMessage('');
    setError(null);
  };

  if (!isReady) {
    return <LoadingSpinner message="Connecting..." />;
  }

  return (
    <div className="min-h-[100dvh]">
      {/* Error toast */}
      {error && (
        <div className="fixed top-2 left-3 right-3 bg-red-900/95 backdrop-blur border border-red-700/60 text-red-200 px-4 py-3 rounded-2xl text-sm z-50 flex items-center justify-between shadow-xl">
          <span className="flex-1">{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-3 text-red-300 font-bold text-lg leading-none touch-manipulation"
          >
            x
          </button>
        </div>
      )}

      {/* LOBBY phase */}
      {phase === 'lobby' && (
        <Lobby
          gameState={gameState}
          onJoin={handleJoin}
          onSubmitGrid={handleSubmitGrid}
          isJoining={isLoading && !hasSubmitted}
          isSubmitting={isLoading}
          hasSubmitted={hasSubmitted}
          alienId={alienId}
        />
      )}

      {/* PLAYING phase */}
      {phase === 'playing' && gameState && !overlay && (
        <div className="flex flex-col items-center min-h-[100dvh] px-4 pt-3 pb-6">
          {/* Title */}
          <h1 className="text-2xl font-extrabold tracking-tight bg-gradient-to-b from-white to-gray-400 bg-clip-text text-transparent mb-2">
            Fair Bingo
          </h1>

          {/* Jackpot banner */}
          <div className="w-full max-w-xs bg-gradient-to-r from-yellow-900/30 via-yellow-800/20 to-yellow-900/30 border border-yellow-700/30 rounded-xl px-4 py-2 mb-3 text-center">
            <p className="text-yellow-500/70 text-[10px] uppercase tracking-widest">Jackpot</p>
            <p className="text-yellow-400 text-xl font-extrabold tabular-nums">
              {gameState.pot.toLocaleString()} <span className="text-xs font-medium text-yellow-500/60">coins</span>
            </p>
          </div>

          {/* Called number display */}
          <NumberDisplay
            latestNumber={gameState.latest_number}
            previousNumber={gameState.previous_number}
          />

          {/* Bingo card */}
          <div className="my-4">
            <BingoCard
              grid={playerGrid}
              markedNumbers={markedNumbers}
              onToggleMark={handleToggleMark}
            />
          </div>

          {/* Claim button */}
          <ClaimButton
            onClaim={handleClaim}
            disabled={gameState.status !== 'active'}
            isClaiming={isLoading}
          />

          {/* Inline chat */}
          <GameChat />
        </div>
      )}

      {/* Result overlays */}
      {overlay === 'won' && (
        <WinnerScreen
          isWinner={true}
          winnerAlienId={alienId}
          pot={gameState?.pot ?? 0}
          onPlayAgain={handlePlayAgain}
        />
      )}

      {overlay === 'kicked' && (
        <KickedScreen message={kickMessage} onPlayAgain={handlePlayAgain} />
      )}

      {overlay === 'finished' && gameState && (
        <WinnerScreen
          isWinner={gameState.winner === alienId}
          winnerAlienId={gameState.winner}
          pot={gameState.pot}
          onPlayAgain={handlePlayAgain}
        />
      )}
    </div>
  );
}
