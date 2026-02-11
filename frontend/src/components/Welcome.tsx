import { BUY_IN_AMOUNT, TOTAL_NUMBERS } from '../config';

interface Props {
  onPlay: () => void;
}

export default function Welcome({ onPlay }: Props) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[100dvh] px-6 py-10">
      {/* Hero */}
      <div className="text-center mb-10">
        <p className="text-gray-500 text-xs uppercase tracking-[0.3em] mb-3">
          Welcome to
        </p>
        <h1 className="text-5xl font-extrabold tracking-tight bg-gradient-to-b from-white via-white to-gray-500 bg-clip-text text-transparent leading-tight">
          Bingo
        </h1>
        <p className="text-lg font-medium bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent mt-1">
          with Aliens
        </p>
      </div>

      {/* Rules */}
      <div className="w-full max-w-xs space-y-3 mb-10">
        <div className="flex gap-3 items-start">
          <span className="text-blue-400/60 text-xs font-bold mt-0.5 shrink-0 w-4 text-right">1</span>
          <p className="text-gray-400 text-sm leading-relaxed">
            Join a lobby and pick <span className="text-white font-medium">9 unique numbers</span> on your 3x3 grid
          </p>
        </div>
        <div className="flex gap-3 items-start">
          <span className="text-blue-400/60 text-xs font-bold mt-0.5 shrink-0 w-4 text-right">2</span>
          <p className="text-gray-400 text-sm leading-relaxed">
            Numbers from 1&ndash;{TOTAL_NUMBERS} are called one at a time
          </p>
        </div>
        <div className="flex gap-3 items-start">
          <span className="text-blue-400/60 text-xs font-bold mt-0.5 shrink-0 w-4 text-right">3</span>
          <p className="text-gray-400 text-sm leading-relaxed">
            Complete a <span className="text-white font-medium">row, column, or diagonal</span> to win
          </p>
        </div>
        <div className="flex gap-3 items-start">
          <span className="text-blue-400/60 text-xs font-bold mt-0.5 shrink-0 w-4 text-right">4</span>
          <p className="text-gray-400 text-sm leading-relaxed">
            Hit <span className="text-white font-medium">BINGO</span> to claim — winner takes the entire pot
          </p>
        </div>
      </div>

      {/* Buy-in info */}
      <p className="text-gray-600 text-xs mb-4">
        Buy-in: {BUY_IN_AMOUNT.toLocaleString()} coins per game
      </p>

      {/* CTA */}
      <button
        onClick={onPlay}
        className="w-full max-w-xs py-4 bg-blue-600 active:bg-blue-700 rounded-2xl font-bold text-lg transition-all active:scale-[0.98] touch-manipulation"
      >
        Play
      </button>
    </div>
  );
}
