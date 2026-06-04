const PALETTE = {
  dark:   ['#C9C9C9','#b8b8b8','#828282','#696969','#424242','#3b3b3b','#2e2e2e','#242424','#1f1f1f','#141414'],
  gray:   ['#f8f9fa','#f1f3f5','#e9ecef','#dee2e6','#ced4da','#adb5bd','#868e96','#495057','#343a40','#212529'],
  red:    ['#fff5f5','#ffe3e3','#ffc9c9','#ffa8a8','#ff8787','#ff6b6b','#fa5252','#f03e3e','#e03131','#c92a2a'],
  pink:   ['#fff0f6','#ffdeeb','#fcc2d7','#faa2c1','#f783ac','#f06595','#e64980','#d6336c','#c2255c','#a61e4d'],
  grape:  ['#f8f0fc','#f3d9fa','#eebefa','#e599f7','#da77f2','#cc5de8','#be4bdb','#ae3ec9','#9c36b5','#862e9c'],
  violet: ['#f3f0ff','#e5dbff','#d0bfff','#b197fc','#9775fa','#845ef7','#7950f2','#7048e8','#6741d9','#5f3dc4'],
  indigo: ['#edf2ff','#dbe4ff','#bac8ff','#91a7ff','#748ffc','#5c7cfa','#4c6ef5','#4263eb','#3b5bdb','#364fc7'],
  blue:   ['#e7f5ff','#d0ebff','#a5d8ff','#74c0fc','#4dabf7','#339af0','#228be6','#1c7ed6','#1971c2','#1864ab'],
  cyan:   ['#e3fafc','#c5f6fa','#99e9f2','#66d9e8','#3bc9db','#22b8cf','#15aabf','#1098ad','#0c8599','#0b7285'],
  teal:   ['#e6fcf5','#c3fae8','#96f2d7','#63e6be','#38d9a9','#20c997','#12b886','#0ca678','#099268','#087f5b'],
  green:  ['#ebfbee','#d3f9d8','#b2f2bb','#8ce99a','#69db7c','#51cf66','#40c057','#37b24d','#2f9e44','#2b8a3e'],
  lime:   ['#f4fce3','#e9fac8','#d8f5a2','#c0eb75','#a9e34b','#94d82d','#82c91e','#74b816','#66a80f','#5c940d'],
  yellow: ['#fff9db','#fff3bf','#ffec99','#ffe066','#ffd43b','#fcc419','#fab005','#f59f00','#f08c00','#e67700'],
  orange: ['#fff4e6','#ffe8cc','#ffd8a8','#ffc078','#ffa94d','#ff922b','#fd7e14','#f76707','#e8590c','#d9480f'],
} as const;

export type MantineAccentKey = keyof typeof PALETTE;

export { PALETTE };

export function resolveDark(accent: MantineAccentKey): Record<string, string> {
  const a = PALETTE[accent];
  return {
    '--fujin-bg-base':              PALETTE.dark[8],
    '--fujin-bg-surface':           PALETTE.dark[7],
    '--fujin-bg-elevated':          PALETTE.dark[6],
    '--fujin-bg-overlay':           PALETTE.dark[5],
    '--fujin-text-primary':         PALETTE.dark[0],
    '--fujin-text-secondary':       PALETTE.dark[1],
    '--fujin-text-muted':           PALETTE.dark[3],
    '--fujin-text-inverse':         PALETTE.dark[8],
    '--fujin-border-subtle':        PALETTE.dark[6],
    '--fujin-border-default':       PALETTE.dark[5],
    '--fujin-border-strong':        PALETTE.dark[3],
    '--fujin-chrome-bg':            PALETTE.dark[7],
    '--fujin-chrome-text':          PALETTE.dark[0],
    '--fujin-chrome-border':        PALETTE.dark[6],
    '--fujin-interactive-default':  a[6],
    '--fujin-interactive-hover':    a[7],
    '--fujin-interactive-active':   a[8],
    '--fujin-interactive-disabled': PALETTE.dark[5],
    '--fujin-status-danger':        PALETTE.red[6],
    '--fujin-status-warning':       PALETTE.yellow[6],
    '--fujin-status-success':       PALETTE.green[6],
    '--fujin-status-info':          PALETTE.blue[6],
    '--fujin-shadow-sm':            '0 1px 2px rgba(0,0,0,0.4)',
    '--fujin-shadow-md':            '0 2px 4px rgba(0,0,0,0.5)',
    '--fujin-shadow-lg':            '0 4px 8px rgba(0,0,0,0.6)',
    '--fujin-layout-content-width': 'clamp(560px, 78vw, 2400px)',
  };
}

export function resolveLight(accent: MantineAccentKey): Record<string, string> {
  const a = PALETTE[accent];
  return {
    '--fujin-bg-base':              PALETTE.gray[3],
    '--fujin-bg-surface':           '#ffffff',
    '--fujin-bg-elevated':          PALETTE.gray[1],
    '--fujin-bg-overlay':           '#ffffff',
    '--fujin-text-primary':         PALETTE.gray[9],
    '--fujin-text-secondary':       PALETTE.gray[7],
    '--fujin-text-muted':           PALETTE.gray[6],
    '--fujin-text-inverse':         PALETTE.gray[0],
    '--fujin-border-subtle':        PALETTE.gray[4],
    '--fujin-border-default':       PALETTE.gray[5],
    '--fujin-border-strong':        PALETTE.gray[7],
    '--fujin-chrome-bg':            PALETTE.gray[8],
    '--fujin-chrome-text':          PALETTE.gray[0],
    '--fujin-chrome-border':        PALETTE.gray[7],
    '--fujin-interactive-default':  a[6],
    '--fujin-interactive-hover':    a[7],
    '--fujin-interactive-active':   a[8],
    '--fujin-interactive-disabled': PALETTE.gray[3],
    '--fujin-status-danger':        PALETTE.red[6],
    '--fujin-status-warning':       PALETTE.yellow[6],
    '--fujin-status-success':       PALETTE.green[6],
    '--fujin-status-info':          PALETTE.blue[6],
    '--fujin-shadow-sm':            '0 1px 2px rgba(0,0,0,0.08)',
    '--fujin-shadow-md':            '0 2px 4px rgba(0,0,0,0.12)',
    '--fujin-shadow-lg':            '0 4px 8px rgba(0,0,0,0.16)',
    '--fujin-layout-content-width': 'clamp(560px, 78vw, 2400px)',
  };
}
