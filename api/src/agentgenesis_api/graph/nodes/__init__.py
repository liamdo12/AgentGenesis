"""Graph node implementations.

Each node module exposes a `build(deps)` factory that returns the async
node callable. All bodies consume `deps.services.X` — the real/stub/noop
swap happens at the services facade, not here.
"""
