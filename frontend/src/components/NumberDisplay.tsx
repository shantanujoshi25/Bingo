import { useEffect, useState } from 'react';

interface Props {
  latestNumber: number | null;
  previousNumber: number | null;
}

export default function NumberDisplay({ latestNumber, previousNumber }: Props) {
  const [animKey, setAnimKey] = useState(0);

  // Re-trigger animation when latest number changes
  useEffect(() => {
    setAnimKey((k) => k + 1);
  }, [latestNumber]);

  return (
    <div className="flex items-center gap-5">
      {previousNumber !== null && (
        <div className="text-center opacity-40">
          <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Prev</p>
          <div className="w-14 h-14 rounded-full bg-gray-700/80 flex items-center justify-center text-lg font-bold text-gray-300">
            {previousNumber}
          </div>
        </div>
      )}

      <div className="text-center">
        <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-1">Called</p>
        {latestNumber !== null ? (
          <div
            key={animKey}
            className="w-24 h-24 rounded-full bg-yellow-500 text-black flex items-center justify-center text-4xl font-extrabold shadow-xl shadow-yellow-500/40 number-pop"
          >
            {latestNumber}
          </div>
        ) : (
          <div className="w-24 h-24 rounded-full bg-gray-800 flex items-center justify-center text-2xl text-gray-600 font-bold">
            --
          </div>
        )}
      </div>
    </div>
  );
}
