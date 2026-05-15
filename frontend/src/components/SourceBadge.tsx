import { cn } from '@/lib/utils';

// Deterministic color from source name
const SOURCE_COLORS: Record<string, { bg: string; text: string }> = {};

const COLOR_PALETTE = [
  { bg: 'bg-blue-100 dark:bg-blue-900/40',    text: 'text-blue-700 dark:text-blue-400'   },
  { bg: 'bg-emerald-100 dark:bg-emerald-900/40', text: 'text-emerald-700 dark:text-emerald-400' },
  { bg: 'bg-violet-100 dark:bg-violet-900/40',   text: 'text-violet-700 dark:text-violet-400' },
  { bg: 'bg-amber-100 dark:bg-amber-900/40',    text: 'text-amber-700 dark:text-amber-400'  },
  { bg: 'bg-rose-100 dark:bg-rose-900/40',      text: 'text-rose-700 dark:text-rose-400'    },
  { bg: 'bg-cyan-100 dark:bg-cyan-900/40',      text: 'text-cyan-700 dark:text-cyan-400'    },
  { bg: 'bg-orange-100 dark:bg-orange-900/40',  text: 'text-orange-700 dark:text-orange-400' },
  { bg: 'bg-teal-100 dark:bg-teal-900/40',      text: 'text-teal-700 dark:text-teal-400'    },
  { bg: 'bg-indigo-100 dark:bg-indigo-900/40',  text: 'text-indigo-700 dark:text-indigo-400' },
  { bg: 'bg-pink-100 dark:bg-pink-900/40',      text: 'text-pink-700 dark:text-pink-400'    },
];

function getSourceColor(name: string) {
  if (!SOURCE_COLORS[name]) {
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
      hash = (hash * 31 + name.charCodeAt(i)) | 0;
    }
    SOURCE_COLORS[name] = COLOR_PALETTE[Math.abs(hash) % COLOR_PALETTE.length];
  }
  return SOURCE_COLORS[name];
}

interface SourceBadgeProps {
  name: string;
  className?: string;
  size?: 'sm' | 'md';
}

export default function SourceBadge({ name, className, size = 'sm' }: SourceBadgeProps) {
  const color = getSourceColor(name);

  return (
    <span
      className={cn(
        'inline-flex items-center font-semibold rounded-md whitespace-nowrap',
        color.bg,
        color.text,
        size === 'sm' ? 'text-2xs px-1.5 py-0.5' : 'text-xs px-2 py-1',
        className,
      )}
    >
      {name}
    </span>
  );
}
