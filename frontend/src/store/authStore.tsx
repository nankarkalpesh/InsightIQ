import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  loginApi,
  signupApi,
  getMeApi,
  type UserAuthInfo,
  type AuthResponse
} from '../lib/api';

const TOKEN_KEY = 'insightiq_auth_token';

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
        if (!savedToken) {
          if (isMounted) setIsLoading(false);
          return;
        }

        const res = await getMeApi(savedToken);
        if (isMounted) {
          setUser(res.user);
          setToken(savedToken);
          setIsLoading(false);
        }
      } catch (err) {
        console.warn('Saved auth token is invalid or expired:', err);
        try {
          localStorage.removeItem(TOKEN_KEY);
        } catch {}
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

  const login = async (email: string, password: string) => {
    const res: AuthResponse = await loginApi(email, password);
    setUser(res.user);
    setToken(res.access_token);
    try {
      localStorage.setItem(TOKEN_KEY, res.access_token);
    } catch (e) {
      console.error('Failed to save token to localStorage:', e);
    }
  };

  const signup = async (email: string, password: string, displayName?: string) => {
    const res: AuthResponse = await signupApi(email, password, displayName);
    setUser(res.user);
    setToken(res.access_token);
    try {
      localStorage.setItem(TOKEN_KEY, res.access_token);
    } catch (e) {
      console.error('Failed to save token to localStorage:', e);
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch (e) {
      console.error('Failed to remove token from localStorage:', e);
    }
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
