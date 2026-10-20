import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { api, tokens } from "./services/api";
import type { User } from "./types";

interface AuthCtx {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  reload: () => Promise<void>;
}

const Ctx = createContext<AuthCtx>(null as unknown as AuthCtx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    if (!tokens.get()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await api<User>("/auth/me/"));
    } catch {
      tokens.clear();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const login = async (username: string, password: string) => {
    const t = await api<{ access: string; refresh: string }>("/auth/login/", { method: "POST", json: { username, password } });
    tokens.set(t.access, t.refresh);
    await reload();
  };

  const logout = () => {
    tokens.clear();
    setUser(null);
  };

  return <Ctx.Provider value={{ user, loading, login, logout, reload }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
