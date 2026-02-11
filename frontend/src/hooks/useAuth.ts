import { useMemo } from 'react';
import { useAlien } from '@alien_org/react';

interface AuthState {
  authToken: string | null;
  alienId: string | null;
  isReady: boolean;
}

export function useAuth(): AuthState {
  const { authToken, isBridgeAvailable } = useAlien();

  return useMemo(() => {
    if (authToken) {
      // Decode JWT payload to get alien_id (sub claim)
      let alienId: string | null = null;
      try {
        const payload = JSON.parse(atob(authToken.split('.')[1]));
        alienId = payload.sub || null;
      } catch {
        alienId = null;
      }
      return { authToken, alienId, isReady: true };
    }

    if (!isBridgeAvailable) {
      // Dev fallback: generate a mock identity when not inside Alien app
      return {
        authToken: 'dev_token',
        alienId: `dev_user_${Math.random().toString(36).slice(2, 8)}`,
        isReady: true,
      };
    }

    // Bridge is available but no token yet — still loading
    return { authToken: null, alienId: null, isReady: false };
  }, [authToken, isBridgeAvailable]);
}
