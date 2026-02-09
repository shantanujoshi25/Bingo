export default function GameChat() {
  return (
    <div className="w-full max-w-xs bg-gray-800/60 rounded-2xl mt-4 flex flex-col" style={{ height: '160px' }}>
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700/50">
        <span className="text-sm font-medium text-gray-400">Game Chat</span>
      </div>

      <div className="flex-1 p-3 flex items-center justify-center">
        <p className="text-gray-600 text-xs text-center">Chat coming soon</p>
      </div>

      <div className="px-3 pb-3">
        <input
          type="text"
          disabled
          placeholder="Message..."
          className="w-full px-3 py-2 bg-gray-700/50 rounded-xl text-sm text-gray-500 placeholder-gray-600"
        />
      </div>
    </div>
  );
}
