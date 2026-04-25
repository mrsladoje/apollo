"""Apollo engine — Plan A bounded context.

Public surface is `engine.api` (`step`, `forecast`, `initial_state`) and the
frozen schemas in `engine.contracts`. Everything else is implementation detail.

`__version__` bumps to "1.0.0" when the real engine replaces the mock per
PLAN-A §13.3.
"""

__version__ = "0.1.0-mock"
