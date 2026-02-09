interface Props {
  onClaim: () => void;
  disabled: boolean;
  isClaiming: boolean;
}

export default function ClaimButton({ onClaim, disabled, isClaiming }: Props) {
  return (
    <button
      onClick={onClaim}
      disabled={disabled || isClaiming}
      className={`
        w-full max-w-xs py-5 rounded-2xl font-extrabold text-2xl uppercase tracking-widest
        transition-all duration-200 active:scale-95 touch-manipulation
        ${
          !disabled
            ? 'bg-red-600 text-white shadow-xl shadow-red-600/40'
            : 'bg-gray-800 text-gray-500'
        }
        ${isClaiming ? 'opacity-70' : ''}
      `}
    >
      {isClaiming ? 'Verifying...' : 'BINGO!'}
    </button>
  );
}
