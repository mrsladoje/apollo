# Apollo saves €X per printer per year (modeled savings)

> Closing demo slide — FR-W.3, NFR-10, ADR-013.

## Headline

**Apollo saves €X per printer per year**
$$ €X = (\text{uptime}_{\text{AI}} - \text{uptime}_{\text{FIXED}}) \times \text{cost\_per\_hour} \times \text{hours\_per\_year} $$

## What we measure

- **uptime_AI** — operating hours per simulated year under Apollo (Universe C)
- **uptime_FIXED** — operating hours per simulated year under Fixed-Schedule
  (Universe B)
- The Dark Twin (Universe A, no maintenance) is plotted for context but is not
  the savings baseline; HP would never run a fleet that way.

## Synthetic-data disclosure (NFR-10)

This is **modeled savings**. Driver vectors come from public weather/grid
sources (NASA POWER, ENTSO-E); failure parameters come from the academic
references below. No proprietary HP failure data is claimed or used.

## Public AM TCO references

1. Academic — Khorasani, M. et al. *"Cost-per-part for direct-metal additive
   manufacturing"*, **CIRP Journal of Manufacturing Science and Technology**,
   2022. Hourly machine cost (€/h) bracket used in our slide.
2. Industry — *Wohlers Report 2024* (Wohlers Associates). AM uptime,
   maintenance event frequency, and unscheduled downtime cost-per-hour
   benchmarks for industrial metal printers in production fleets.

## Speaker notes

> "The number on screen is **modeled savings** — we built a digital twin and
> ran the same workload under three policies. Apollo (Universe C) saves €X
> per printer per year vs. the Fixed-Schedule baseline. The cost-per-hour
> bracket comes from Khorasani 2022; the uptime delta is the integral of the
> health curves you just saw. We aren't quoting proprietary HP numbers —
> everything is reproducible from the public driver feeds."
