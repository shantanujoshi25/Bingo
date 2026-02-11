import { AlienProvider } from '@alien_org/react';
import GameFlow from './components/GameFlow';

function App() {
  return (
    <AlienProvider>
      <div className="min-h-screen bg-gray-900 text-white">
        <GameFlow />
      </div>
    </AlienProvider>
  );
}

export default App;
