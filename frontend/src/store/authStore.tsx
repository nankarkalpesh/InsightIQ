import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  loginApi,
  signupApi,
  getMeApi,
  refreshTokenApi,
  logoutBackendApi,
  TOKEN_KEY,
  REFRESH_TOKEN_KEY,
  type UserAuthInfo,
  type AuthResponse
} from '../lib/api';

export interface AuthContextType {
  user: UserAuthInfo | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserAuthInfo | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Restore authenticated session on app initialization
  useEffect(() => {
    let isMounted = true;

    const restoreAuthSession = async () => {
      try {
        const savedToken = localStorage.getItem(TOKEN_KEY);
        const savedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);

        if (!savedToken && !savedRefreshToken) {
          if (isMounted) setIsLoading(false);
          return;
        }

        if (savedToken) {
          try {
            const res = await getMeApi(savedToken);
            if (isMounted) {
              setUser(res.user);
              setToken(savedToken);
              setIsLoading(false);
            }
            return;
          } catch (meErr) {
            console.warn('Saved access token expired, attempting refresh token renewal...', meErr);
          }
        }

        // Access token expired or missing, try refresh token renewal
        if (savedRefreshToken) {
          try {
            const refreshRes = await refreshTokenApi(savedRefreshToken);
            const meRes = await getMeApi(refreshRes.access_token);
            if (isMounted) {
              setUser(meRes.user);
              setToken(refreshRes.access_token);
              setIsLoading(false);
            }
            return;
          } catch (refreshErr) {
            console.warn('Refresh token is invalid or expired:', refreshErr);
          }
        }

        // If all restoration attempts fail, clear auth tokens
        try {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(REFRESH_TOKEN_KEY);
        } catch {}

        if (isMounted) {
          setUser(null);
          setToken(null);
          setIsLoading(false);
        }
      } catch (err) {
        console.warn('Unexpected error during auth session restoration:', err);
        if (isMounted) {
          setUser(null);
          setToken(null);
          setIsLoading(false);
        }
      }
    };

    restoreAuthSession();

    return () => {
      isMounted = false;
    };
  }, []);

  // Proactive background refresh timer (renew access token every 15 minutes while active)
  useEffect(() => {
    if (!token || !user) return;

    const REFRESH_INTERVAL_MS = 15 * 60 * 1000; // 15 minutes
    const interval = setInterval(async () => {
      try {
        const savedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
        if (savedRefreshToken) {
          const res = await refreshTokenApi(savedRefreshToken);
          if (res.access_token) {
            setToken(res.access_token);
          }
        }
      } catch (e) {
        console.warn('Proactive background token refresh failed:', e);
      }
    }, REFRESH_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [token, user]);

  const login = async (email: string, password: string) => {
    const res: AuthResponse = await loginApi(email, password);
    setUser(res.user);
    setToken(res.access_token);
    try {
      localStorage.setItem(TOKEN_KEY, res.access_token);
      if (res.refresh_token) {
        localStorage.setItem(REFRESH_TOKEN_KEY, res.refresh_token);
      }
    } catch (e) {
      console.error('Failed to save auth tokens to localStorage:', e);
    }
  };

  const signup = async (email: string, password: string, displayName?: string) => {
    const res: AuthResponse = await signupApi(email, password, displayName);
    setUser(res.user);
    setToken(res.access_token);
    try {
      localStorage.setItem(TOKEN_KEY, res.access_token);
      if (res.refresh_token) {
        localStorage.setItem(REFRESH_TOKEN_KEY, res.refresh_token);
      }
    } catch (e) {
      console.error('Failed to save auth tokens to localStorage:', e);
    }
  };

  const logout = () => {
    const savedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (savedRefreshToken) {
      logoutBackendApi(savedRefreshToken);
    }
    setUser(null);
    setToken(null);
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
    } catch (e) {
      console.error('Failed to remove auth token keys from localStorage:', e);
    }
    window.dispatchEvent(new Event('insightiq_logout'));
  };


  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        signup,
        logout
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
