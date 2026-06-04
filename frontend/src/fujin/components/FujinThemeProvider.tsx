import React, { createContext, useContext } from 'react';
import { MantineProvider, useComputedColorScheme, useMantineColorScheme } from '@mantine/core';
import { createFujinTheme, type FujinPreset, type MantineAccentKey } from '../themes/createFujinTheme';
import '@mantine/core/styles.css';

interface FujinThemeContextValue {
  mode:   'light' | 'dark';
  toggle: () => void;
  preset: FujinPreset;
}

const FujinThemeContext = createContext<FujinThemeContextValue | null>(null);

export function useFujinTheme(): FujinThemeContextValue {
  const ctx = useContext(FujinThemeContext);
  if (!ctx) throw new Error('useFujinTheme must be used inside FujinThemeProvider');
  return ctx;
}

export interface FujinThemeProviderProps {
  children:     React.ReactNode;
  preset?:      MantineAccentKey;
  defaultMode?: 'light' | 'dark';
}

function FujinVarInjector({ preset, children }: { preset: FujinPreset; children: React.ReactNode }) {
  const scheme = useComputedColorScheme('dark');
  const { toggleColorScheme } = useMantineColorScheme();
  const vars = scheme === 'dark' ? preset.dark : preset.light;

  return (
    <FujinThemeContext.Provider value={{ mode: scheme, toggle: toggleColorScheme, preset }}>
      <div style={{ ...vars, minHeight: '100vh' } as React.CSSProperties}>
        {children}
      </div>
    </FujinThemeContext.Provider>
  );
}

export function FujinThemeProvider({
  children,
  preset:      accentKey  = 'violet',
  defaultMode             = 'dark',
}: FujinThemeProviderProps) {
  const theme = createFujinTheme(accentKey);
  return (
    <MantineProvider theme={theme.mantine} defaultColorScheme={defaultMode}>
      <FujinVarInjector preset={theme}>
        {children}
      </FujinVarInjector>
    </MantineProvider>
  );
}
