interface Props {
  message: string;
  onPlayAgain: () => void;
}

export default function KickedScreen({ message, onPlayAgain }: Props) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[100dvh] px-6 gap-5">
      <div className="w-20 h-20 rounded-full bg-red-900/40 flex items-center justify-center">
        <span className="text-4xl font-bold text-red-400">X</span>
      </div>
      <h1 className="text-2xl font-bold text-red-400">Invalid Claim</h1>
      <p className="text-gray-400 text-center max-w-xs text-sm leading-relaxed">{message}</p>
      <p className="text-gray-600 text-xs text-center">
        You've been removed from the game for a false bingo claim.
      </p>
      <button
        onClick={onPlayAgain}
        className="w-full max-w-xs py-4 bg-blue-600 active:bg-blue-700 rounded-2xl font-bold text-xl transition-all active:scale-[0.98] touch-manipulation mt-6"
      >
        Try Again
      </button>
    </div>
  );
}
