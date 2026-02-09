interface Props {
  isWinner: boolean;
  winnerAlienId: string | null;
  pot: number;
  onPlayAgain: () => void;
}

export default function WinnerScreen({ isWinner, winnerAlienId, pot, onPlayAgain }: Props) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[100dvh] px-6 gap-5">
      {isWinner ? (
        <>
          <div className="text-7xl font-black tracking-tighter bg-gradient-to-b from-yellow-300 to-amber-500 bg-clip-text text-transparent">
            BINGO!
          </div>
          <h1 className="text-2xl font-bold text-green-400">You Won!</h1>
          <p className="text-5xl font-extrabold text-yellow-400">
            +{pot.toLocaleString()}
          </p>
          <p className="text-gray-500 text-sm">Alien coins added to your balance</p>
        </>
      ) : (
        <>
          <h1 className="text-3xl font-bold text-gray-300">Game Over</h1>
          {winnerAlienId ? (
            <div className="text-center space-y-2">
              <p className="text-yellow-400 font-bold text-lg">{winnerAlienId}</p>
              <p className="text-gray-400">
                won the pot of{' '}
                <span className="text-green-400 font-bold">{pot.toLocaleString()}</span> coins
              </p>
            </div>
          ) : (
            <p className="text-gray-400 text-center">
              No winner this round. The house keeps the pot.
            </p>
          )}
        </>
      )}

      <button
        onClick={onPlayAgain}
        className="w-full max-w-xs py-4 bg-blue-600 active:bg-blue-700 rounded-2xl font-bold text-xl transition-all active:scale-[0.98] touch-manipulation mt-6"
      >
        Play Again
      </button>
    </div>
  );
}
