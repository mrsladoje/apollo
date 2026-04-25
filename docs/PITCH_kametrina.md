## Cascade example

The HP Metal Jet S100 has dashboards full of sensors. When something goes wrong, the dashboard alarms. But the dashboard alarms on the part that's visibly broken — almost never the part that actually started the problem.

Here's the canonical example we use in the demo:

1. The insulation in the thermal subsystem starts degrading. Heat starts leaking out.
2. The heater has to work harder to maintain temperature. It runs hotter than designed.
3. The hot enclosure makes the binder ink (the glue that holds the metal powder together) less viscous — runnier.
4. Runnier binder messes up the nozzle spray pattern. Eventually the nozzle clogs.
5. The dashboard alarms: "NOZZLE FAILURE."

The maintenance engineer swaps the nozzle. Two days later — another nozzle failure. They swap it again. Another failure. They scratch their head. They never look at the insulation, because nothing alarmed on it.

## System parts

Action - Subsystem - Components
Metal powder - Recoating - Blade, Motor
Binding spray - Printhead - Nozzle, Resistor
Cure Binding - Thermal - Insulator, Heater

## Equations for degradation

1. Exponential decay
- like rubber gum (same amount every day), but exponential since it approaches zero asympthotically
- blade (proven to degrade in this way in literature), insulation panel (sustained pressure)

2. Weibull (probability)
- car batteries usually die after 5 seasons - until then they work normally and then just die - that being said, some things are most likely to die after a specific amount of time
- motor (bearings in general, there is an international standard even - ISO 281 - bearing standard), nozzle (it works until it doesn't), blade (in case of impact events)

3. Coffin-Manson (thermal cycles)
- not time-dependent, but on number of thermal cycles
- the bigger the temp swing per cycle - the less cycles needed to die
- thermal firing resistors (temp swing 100->300degC), heating element (bigger swings), used along with PINN

## Bit-identical determinism

Allows for proper testing, policy comparison, etc etc...