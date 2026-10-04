/**
 * In-memory limiter for the single-instance website process. It resets on
 * restart and is not shared between instances; message texts are never stored,
 * only request timestamps per client key.
 */

export type LimitConfig = {
  perKeyShort: { limit: number; windowMs: number };
  perKeyDaily: { limit: number; windowMs: number };
  globalMinute: { limit: number; windowMs: number };
  globalDaily: { limit: number; windowMs: number };
  maxTrackedKeys: number;
};

export const DEFAULT_LIMITS: LimitConfig = {
  perKeyShort: { limit: 20, windowMs: 10 * 60 * 1000 },
  perKeyDaily: { limit: 60, windowMs: 24 * 60 * 60 * 1000 },
  globalMinute: { limit: 30, windowMs: 60 * 1000 },
  globalDaily: { limit: 1500, windowMs: 24 * 60 * 60 * 1000 },
  maxTrackedKeys: 10_000,
};

export type LimitDecision = { allowed: true } | { allowed: false; reason: "client" | "global" };

function prune(stamps: number[], now: number, windowMs: number): number[] {
  const from = now - windowMs;
  let index = 0;
  while (index < stamps.length && stamps[index] <= from) index += 1;
  return index === 0 ? stamps : stamps.slice(index);
}

function countSince(stamps: number[], now: number, windowMs: number): number {
  const from = now - windowMs;
  let count = 0;
  for (let i = stamps.length - 1; i >= 0 && stamps[i] > from; i -= 1) count += 1;
  return count;
}

export class ConsultantRateLimiter {
  private readonly perKey = new Map<string, number[]>();
  private global: number[] = [];

  constructor(
    private readonly config: LimitConfig = DEFAULT_LIMITS,
    private readonly now: () => number = Date.now,
  ) {}

  /** Records the attempt only when it is allowed. Any internal error denies. */
  consume(key: string): LimitDecision {
    try {
      const now = this.now();
      const { perKeyShort, perKeyDaily, globalMinute, globalDaily } = this.config;

      this.global = prune(this.global, now, globalDaily.windowMs);
      if (
        this.global.length >= globalDaily.limit ||
        countSince(this.global, now, globalMinute.windowMs) >= globalMinute.limit
      ) {
        return { allowed: false, reason: "global" };
      }

      const existing = this.perKey.get(key);
      const stamps = existing ? prune(existing, now, perKeyDaily.windowMs) : [];
      if (!existing && this.perKey.size >= this.config.maxTrackedKeys) {
        this.evictIdle(now);
        if (this.perKey.size >= this.config.maxTrackedKeys) return { allowed: false, reason: "global" };
      }
      if (
        stamps.length >= perKeyDaily.limit ||
        countSince(stamps, now, perKeyShort.windowMs) >= perKeyShort.limit
      ) {
        this.perKey.set(key, stamps);
        return { allowed: false, reason: "client" };
      }

      stamps.push(now);
      this.perKey.set(key, stamps);
      this.global.push(now);
      return { allowed: true };
    } catch {
      return { allowed: false, reason: "global" };
    }
  }

  private evictIdle(now: number): void {
    for (const [key, stamps] of this.perKey) {
      if (prune(stamps, now, this.config.perKeyDaily.windowMs).length === 0) this.perKey.delete(key);
    }
  }
}
