import { useState, useEffect } from 'react';
import { TOTAL_NUMBERS, BUY_IN_AMOUNT } from '../config';
import type { GameStatus } from '../types';

interface Props {
  gameState: GameStatus | null;
  onJoin: () => void;
  onSubmitGrid: (grid: number[][]) => void;
  isJoining: boolean;
  isSubmitting: boolean;
  hasSubmitted: boolean;
  alienId: string | null;
}

function generateRandomGrid(): number[][] {
  const pool = Array.from({ length: TOTAL_NUMBERS }, (_, i) => i + 1);
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }
  const picked = pool.slice(0, 9);
  return [picked.slice(0, 3), picked.slice(3, 6), picked.slice(6, 9)];
}

function NumberInput({
  value,
  onChange,
  usedNumbers,
  disabled,
}: {
  value: number | null;
  onChange: (num: number | null) => void;
  usedNumbers: Set<number>;
  disabled: boolean;
}) {
  const [raw, setRaw] = useState(value !== null ? String(value) : '');
  const [error, setError] = useState('');

  // Sync raw when value changes externally (e.g. random pre-fill)
  useEffect(() => {
    setRaw(value !== null ? String(value) : '');
    setError('');
  }, [value]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setRaw(val);
    setError('');

    if (val === '') {
      onChange(null);
      return;
    }

    const num = parseInt(val, 10);
    if (isNaN(num) || num < 1 || num > TOTAL_NUMBERS) {
      setError(`1-${TOTAL_NUMBERS}`);
      return;
    }
    if (usedNumbers.has(num)) {
      setError('Taken');
      return;
    }
    onChange(num);
  };

  return (
    <div className="flex flex-col items-center">
      <input
        type="number"
        inputMode="numeric"
        min={1}
        max={TOTAL_NUMBERS}
        value={raw}
        onChange={handleChange}
        disabled={disabled}
        placeholder="--"
        className={`w-full aspect-square rounded-2xl text-center text-2xl font-bold touch-manipulation outline-none transition-all
          ${disabled ? 'bg-gray-800/30 text-gray-500 opacity-50' : value !== null && !error ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-300'}
          ${error ? 'ring-2 ring-red-500/60' : 'focus:ring-2 focus:ring-blue-500/60'}
        `}
      />
      {error && <span className="text-red-400 text-[10px] mt-0.5">{error}</span>}
    </div>
  );
}

function CountdownTimer({ deadline }: { deadline: string }) {
  const [remaining, setRemaining] = useState('');

  useEffect(() => {
    const update = () => {
      const diff = new Date(deadline + 'Z').getTime() - Date.now();
      if (diff <= 0) {
        setRemaining('0:00');
        return;
      }
      const mins = Math.floor(diff / 60000);
      const secs = Math.floor((diff % 60000) / 1000);
      setRemaining(`${mins}:${String(secs).padStart(2, '0')}`);
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [deadline]);

  return (
    <span className="tabular-nums font-bold text-yellow-400">{remaining}</span>
  );
}

export default function Lobby({
  gameState,
  onJoin,
  onSubmitGrid,
  isJoining,
  isSubmitting,
  hasSubmitted,
  alienId,
}: Props) {
  const [grid, setGrid] = useState<(number | null)[][]>(generateRandomGrid);

  const isInProgress = gameState?.status === 'in_progress';
  const isForming = gameState?.status === 'forming';
  const hasJoined = !!gameState;
  const allFilled = grid.every((row) => row.every((cell) => cell !== null));

  const handleCellChange = (row: number, col: number, num: number | null) => {
    setGrid((prev) => {
      const next = prev.map((r) => [...r]);
      next[row][col] = num;
      return next;
    });
  };

  const handleSubmit = () => {
    if (!allFilled) return;
    const finalGrid = grid.map((row) => row.map((n) => n!));
    onSubmitGrid(finalGrid);
  };

  const players = gameState?.players ? Object.values(gameState.players) : [];

  return (
    <div className="flex flex-col items-center min-h-[100dvh] px-4 py-6">
      {/* Title */}
      <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-b from-white to-gray-400 bg-clip-text text-transparent mb-1">
        Fair Bingo
      </h1>
      <p className="text-gray-500 text-xs mb-2">
        Buy-in: {BUY_IN_AMOUNT.toLocaleString()} coins
      </p>

      {/* Game in progress banner */}
      {isInProgress && (
        <div className="w-full max-w-sm bg-yellow-900/40 border border-yellow-700/50 rounded-xl px-4 py-3 mb-4 text-center">
          <p className="text-yellow-300 font-medium text-sm">Game in progress</p>
          <p className="text-yellow-500/70 text-xs mt-1">Waiting for next round...</p>
        </div>
      )}

      {/* Join button (pre-join state) */}
      {!hasJoined && (
        <div className="flex flex-col items-center gap-4 mt-8">
          <p className="text-gray-400 text-sm text-center max-w-[260px] leading-relaxed">
            Join the lobby, pick your 9 numbers on the 3x3 grid, and compete for the pot!
          </p>
          <button
            onClick={onJoin}
            disabled={isJoining}
            className="w-64 py-4 bg-blue-600 active:bg-blue-700 disabled:opacity-50 rounded-2xl font-bold text-xl transition-all active:scale-[0.98] touch-manipulation"
          >
            {isJoining ? 'Joining...' : 'Join Game'}
          </button>
        </div>
      )}

      {/* After joining — reordered: timer → players → jackpot → grid → button */}
      {hasJoined && !isInProgress && (
        <>
          {/* 1. Countdown timer */}
          {isForming && gameState.forming_deadline && (
            <div className="flex items-center gap-2 mb-3">
              <span className="text-gray-400 text-xs">Time to pick:</span>
              <CountdownTimer deadline={gameState.forming_deadline} />
            </div>
          )}

          {/* 2. Player list */}
          <div className="w-full max-w-xs mb-4">
            <h3 className="text-gray-400 text-xs font-medium mb-2 uppercase tracking-wide">
              Players ({gameState.player_count})
            </h3>
            <div className="space-y-1.5">
              {players.map((p) => (
                <div
                  key={p.alien_id}
                  className="flex items-center justify-between bg-gray-800/60 rounded-lg px-3 py-2"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className={`text-sm font-mono truncate ${p.alien_id === alienId ? 'text-blue-400' : 'text-gray-300'}`}>
                      {p.alien_id === alienId ? 'You' : p.alien_id.slice(0, 12)}
                    </span>
                    <span className="text-yellow-500/80 text-[10px] font-medium shrink-0">
                      {BUY_IN_AMOUNT.toLocaleString()}
                    </span>
                  </div>
                  <span className={`text-xs font-medium shrink-0 ml-2 ${p.ready ? 'text-green-400' : 'text-gray-500'}`}>
                    {p.ready ? 'Ready' : 'Picking...'}
                  </span>
                </div>
              ))}
              {players.length === 0 && (
                <p className="text-gray-600 text-xs text-center py-2">
                  No players yet
                </p>
              )}
            </div>
          </div>

          {/* 3. Jackpot display */}
          <div className="w-full max-w-xs bg-gradient-to-r from-yellow-900/30 via-yellow-800/20 to-yellow-900/30 border border-yellow-700/30 rounded-xl px-4 py-3 mb-4 text-center">
            <p className="text-yellow-500/70 text-[10px] uppercase tracking-widest">Jackpot</p>
            <p className="text-yellow-400 text-2xl font-extrabold tabular-nums">
              {gameState.pot.toLocaleString()} <span className="text-sm font-medium text-yellow-500/60">coins</span>
            </p>
          </div>

          {/* 4. 3x3 Grid of number inputs */}
          <p className="text-gray-400 text-xs mb-3 text-center">
            Enter 9 unique numbers (1-{TOTAL_NUMBERS}). Position = your bingo card.
          </p>
          <div className="grid grid-cols-3 gap-3 w-full max-w-xs mb-4">
            {grid.map((row, rIdx) =>
              row.map((val, cIdx) => (
                <NumberInput
                  key={`${rIdx}-${cIdx}`}
                  value={val}
                  onChange={(num) => handleCellChange(rIdx, cIdx, num)}
                  usedNumbers={
                    new Set(
                      grid
                        .flat()
                        .filter(
                          (n, idx): n is number =>
                            n !== null && idx !== rIdx * 3 + cIdx
                        )
                    )
                  }
                  disabled={hasSubmitted || isInProgress}
                />
              ))
            )}
          </div>

          {/* 5. PLAY / Submit button */}
          {!hasSubmitted ? (
            <button
              onClick={handleSubmit}
              disabled={!allFilled || isSubmitting}
              className="w-full max-w-xs py-4 bg-green-600 active:bg-green-700 disabled:opacity-40 disabled:bg-gray-700 rounded-2xl font-bold text-lg transition-all active:scale-[0.98] touch-manipulation"
            >
              {isSubmitting ? 'Submitting...' : 'PLAY'}
            </button>
          ) : (
            <div className="w-full max-w-xs py-4 bg-gray-700 rounded-2xl text-center">
              <p className="text-green-400 font-bold text-lg">Ready!</p>
              <p className="text-gray-400 text-xs mt-1">Waiting for other players...</p>
            </div>
          )}

          {/* 6. Ready count */}
          <div className="w-full max-w-xs mt-4 text-center text-xs text-gray-500">
            <span>Ready: {gameState.ready_count}/{gameState.player_count}</span>
          </div>
        </>
      )}
    </div>
  );
}
