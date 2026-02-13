interface Props {
  grid: number[][];
  markedNumbers: Set<number>;
  onToggleMark: (num: number) => void;
}

export default function BingoCard({ grid, markedNumbers, onToggleMark }: Props) {
  return (
    <div className="w-full max-w-md">
      <div className="grid grid-cols-3 gap-4">
        {grid.map((row, rIdx) =>
          row.map((num, cIdx) => {
            const isMarked = markedNumbers.has(num);

            return (
              <button
                key={`${rIdx}-${cIdx}`}
                onClick={() => onToggleMark(num)}
                className={`
                  bingo-ball w-[5.5rem] h-[5.5rem] rounded-full text-3xl font-extrabold
                  flex items-center justify-center
                  transition-all duration-200 touch-manipulation
                  ${isMarked
                    ? 'bg-gradient-to-b from-purple-400 to-purple-700 text-white shadow-lg shadow-purple-500/40 scale-[1.03]'
                    : 'bg-gradient-to-b from-white to-gray-200 text-gray-900 active:from-gray-100 active:to-gray-300'
                  }
                `}
              >
                {num}
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
