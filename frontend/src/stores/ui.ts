import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UiState {
  theme: "light" | "dark";
  toggleTheme: () => void;
}

function apply(theme: "light" | "dark") {
  document.documentElement.dataset.theme = theme;
}

export const useUi = create<UiState>()(
  persist(
    (set, get) => ({
      theme: "light",
      toggleTheme: () => {
        const next = get().theme === "light" ? "dark" : "light";
        apply(next);
        set({ theme: next });
      },
    }),
    {
      name: "ekip-ui",
      onRehydrateStorage: () => (state) => apply(state?.theme ?? "light"),
    },
  ),
);
