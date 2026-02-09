import { useState, useEffect } from 'react';

interface AuthState {
  authToken: string | null;
  alienId: string | null;
  isReady: boolean;
}

export function useAuth(): AuthState {
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [alienId, setAlienId] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    // In Alien Mini App, the JWT is injected into window.__ALIEN_AUTH_TOKEN__
    // For development, we fall back to a mock token
    const checkAuth = () => {
      const win = window as unknown as Record<string, unknown>;
      const token = win.__ALIEN_AUTH_TOKEN__ as string | undefined;

      if (token) {
        setAuthToken(token);
        // Decode JWT payload to get alien_id (sub claim)
        try {
          const payload = JSON.parse(atob(token.split('.')[1]));
          setAlienId(payload.sub || null);
        } catch {
          setAlienId(null);
        }
      } else {
        // Dev fallback: generate a mock identity
        setAuthToken('dev_token');
        setAlienId(`dev_user_${Math.random().toString(36).slice(2, 8)}`);
      }
      setIsReady(true);
    };

    // Small delay to allow Mini App host to inject token
    const timer = setTimeout(checkAuth, 100);
    return () => clearTimeout(timer);
  }, []);

  return { authToken, alienId, isReady };
}
