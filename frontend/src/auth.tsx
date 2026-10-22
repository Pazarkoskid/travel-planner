import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { api, ApiError, tokens } from "./services/api";

const USER_KEY = "tpm_user";
const cachedUser = (): User | null => {
  try { return JSON.parse(localStorage.getItem(USER_KEY) || "null"); } catch { return null; }
};
const saveUser = (u: User | null) => {
  try { u ? localStorage.setItem(USER_KEY, JSON.stringify(u)) : localStorage.removeItem(USER_KEY); } catch { /* приватен режим */ }
};
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
      const u = await api<User>("/auth/me/");
      saveUser(u);
      setUser(u);
    } catch (e) {
      if (e instanceof ApiError) {
        // Серверот вели дека најавата не важи → одјава.
        tokens.clear();
        saveUser(null);
        setUser(null);
      } else {
        // Мрежна грешка (офлајн): остани најавен со последно познатиот профил.
        setUser(cachedUser());
      }
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
    saveUser(null);
    setUser(null);
  };

  return <Ctx.Provider value={{ user, loading, login, logout, reload }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
