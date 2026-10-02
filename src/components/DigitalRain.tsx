/**
 * Soft binary rain backdrop for AI-related sections.
 * Deterministic columns (SSR-safe). Lightweight CSS animation only.
 */

type Column = {
  id: string;
  left: string;
  duration: number;
  delay: number;
  fontSize: number;
  opacity: number;
  text: string;
};

function seededRandom(seed: number) {
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

function buildColumns(count: number, seed: number): Column[] {
  const rand = seededRandom(seed);
  const columns: Column[] = [];
  for (let i = 0; i < count; i++) {
    const len = 18 + Math.floor(rand() * 22);
    let text = "";
    for (let j = 0; j < len; j++) {
      text += rand() > 0.48 ? "1" : "0";
      if (j < len - 1) text += "\n";
    }
    columns.push({
      id: `c${i}`,
      left: `${(i + 0.5) * (100 / count)}%`,
      duration: 16 + rand() * 14,
      delay: -(rand() * 18),
      fontSize: 10 + Math.floor(rand() * 4),
      opacity: 0.08 + rand() * 0.1,
      text,
    });
  }
  return columns;
}

const COLUMNS = buildColumns(14, 42);

export function DigitalRain({ className = "" }: { className?: string }) {
  return (
    <div
      className={`digital-rain pointer-events-none absolute inset-0 overflow-hidden ${className}`}
      aria-hidden="true"
    >
      <div className="digital-rain__fade absolute inset-0" />
      {COLUMNS.map((col) => (
        <pre
          key={col.id}
          className="digital-rain__col absolute top-0 -translate-x-1/2 select-none font-mono leading-tight"
          style={{
            left: col.left,
            fontSize: `${col.fontSize}px`,
            opacity: col.opacity,
            animationDuration: `${col.duration}s`,
            animationDelay: `${col.delay}s`,
          }}
        >
          {col.text}
        </pre>
      ))}
    </div>
  );
}
