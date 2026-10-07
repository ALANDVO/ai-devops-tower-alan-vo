import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api, User } from '../api/client';

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, role: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('devops_token');
    if (token) {
      api.me()
        .then(setUser)
        .catch(() => localStorage.removeItem('devops_token'))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email: string, role: string) => {
    const res = await api.login(email, role);
    localStorage.setItem('devops_token', res.access_token);
    const me = await api.me();
    setUser(me);
  };

  const logout = () => {
    localStorage.removeItem('devops_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
