import { createTheme, type MantineThemeOverride } from '@mantine/core';
import { resolveDark, resolveLight, type MantineAccentKey } from './palette';
import tokens from '../tokens.json';

export type { MantineAccentKey };

export interface FujinPreset {
  key:     MantineAccentKey;
  dark:    Record<string, string>;
  light:   Record<string, string>;
  mantine: MantineThemeOverride;
}

export function createFujinTheme(accent: MantineAccentKey): FujinPreset {
  const dark  = resolveDark(accent);
  const light = resolveLight(accent);

  const mantine = createTheme({
    primaryColor:        accent,
    defaultRadius:       0,
    fontFamily:          tokens.typography.fontFamily.base,
    fontFamilyMonospace: tokens.typography.fontFamily.mono,
  });

  return { key: accent, dark, light, mantine };
}
