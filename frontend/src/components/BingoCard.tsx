interface Props {
  grid: number[][];
  markedNumbers: Set<number>;
  onToggleMark: (num: number) => void;
}

export default function BingoCard({ grid, markedNumbers, onToggleMark }: Props) {
  return (
    <div className="w-full max-w-sm">
      <div className="grid grid-cols-3 gap-4">
        {grid.map((row, rIdx) =>
          row.map((num, cIdx) => {
            const isMarked = markedNumbers.has(num);

            return (
              <button
                key={`${rIdx}-${cIdx}`}
                onClick={() => onToggleMark(num)}
                className={`
                  aspect-square rounded-2xl text-3xl font-bold
                  transition-all duration-200 touch-manipulation
                  ${isMarked
                    ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30 scale-[1.03]'
                    : 'bg-gray-800 text-white active:bg-gray-700'
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
