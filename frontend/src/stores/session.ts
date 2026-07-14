import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "../lib/api";

interface SessionState {
  token: string | null;
  user: User | null;
  signIn: (token: string, user: User) => void;
  clear: () => void;
}

export const useSession = create<SessionState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      signIn: (token, user) => set({ token, user }),
      clear: () => set({ token: null, user: null }),
    }),
    { name: "ekip-session" },
  ),
);
