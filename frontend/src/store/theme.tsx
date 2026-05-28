import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type AppThemeMode = "light" | "dark";

type ThemeContextValue = {
  mode: AppThemeMode;
  setMode: (mode: AppThemeMode) => void;
  toggleMode: () => void;
};

const THEME_STORAGE_KEY = "vpnbotx.theme";

const ThemeContext = createContext<ThemeContextValue | null>(null);

function getInitialTheme(): AppThemeMode {
  const saved = localStorage.getItem(THEME_STORAGE_KEY);
  if (saved === "light" || saved === "dark") {
    return saved;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<AppThemeMode>(getInitialTheme);

  function setMode(nextMode: AppThemeMode) {
    setModeState(nextMode);
    localStorage.setItem(THEME_STORAGE_KEY, nextMode);
  }

  useEffect(() => {
    document.documentElement.dataset.theme = mode;
  }, [mode]);

  const value = useMemo(
    () => ({
      mode,
      setMode,
      toggleMode: () => setMode(mode === "dark" ? "light" : "dark"),
    }),
    [mode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useThemeMode() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useThemeMode must be used inside ThemeProvider");
  }
  return context;
}
