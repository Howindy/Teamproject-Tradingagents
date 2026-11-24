"""Run-local execution context for one analysis (C-03, FR-03).

A ``RunContext`` is the ephemeral scope that owns this analysis's availability
registry (C-07) and any other run-local observations. It is bound with
``contextvars`` (context-local), never a process-global mutable "current run", so
independent concurrent analyses never share scope state and explicit internal
delegation can share one deliberately.

Contract (D2 C-03 / IF-02 / IF-03):

* Each independent analysis creates its own ``RunContext`` and a fresh registry.
* ``current()`` returns the scope bound in this execution context, or ``None``.
* Entering binds the scope and remembers the previously bound one; leaving
  restores it. ``finish()`` is idempotent: it restores the prior binding exactly
  once and never closes a resource twice.
* Resource ownership is the ENTRY's, not this object's. The entry that opened any
  run-owned resource closes it in its own ``finally``; ``finish`` only restores the
  binding and never releases entry-owned resources. There is no arbitrary
  cleanup hook here.
* No persistent identity, timers, statistics, manifest, formal decision or FR-01
  reuse is added. Run infrastructure is never serialized into graph state.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Literal

logger = logging.getLogger(__name__)

_current: ContextVar[RunContext | None] = ContextVar(
    "tradingagents_run_context", default=None
)

# Sentinel for "no explicit delegate target given".
_UNSET = object()


class RunContext:
    """One analysis's ephemeral run scope; context manager.

    Construction alone creates no analysis binding. ``__enter__`` binds the scope
    in the current execution context (remembering any previous binding) and
    ``__exit__``/``finish`` restore it. ``registry`` is this run's availability
    registry, created once per scope.
    """

    def __init__(self, delegate=_UNSET, analysis_context=None):
        # Internal explicit-sharing: a delegated scope aliases the target's
        # registry instead of making a new one, so an explicitly shared portion of
        # a run reads/writes the same availability state.
        if delegate is not _UNSET and delegate is not None:
            self._registry = delegate.registry
            self._shared_with = delegate
        else:
            from tradingagents.dataflows.availability import AvailabilityRegistry

            # A minimal internal analysis identity (existing ticker/date/range) lets
            # the registry judge necessity-target eligibility. It is NOT a public
            # input, product schema, or configuration item; the real entry supplies
            # it once the entry-scope binding wave lands.
            self._registry = AvailabilityRegistry(analysis_context=analysis_context)
            self._shared_with = None
        self._token = None
        self._finished = False

    @property
    def registry(self):
        """This run's ``AvailabilityRegistry`` (or the delegating scope's)."""
        return self._registry

    # ------------------------------------------------------------------ #
    # Binding lifecycle                                                   #
    # ------------------------------------------------------------------ #
    def __enter__(self) -> RunContext:
        self._token = _current.set(self)
        return self

    def __exit__(self, exc_type, exc, tb) -> Literal[False]:
        self.finish()
        return False  # never suppress a primary error

    def finish(self) -> None:
        """Restore the previous binding once; idempotent and exception-safe.

        Only the binding is restored here; entry-owned resources are released by
        the entry's own ``finally``, not by this method. A second ``finish`` is a
        no-op and does not disturb a binding established after the first finish
        (the restore token is consumed exactly once).

        A token reset can only fail for unsupported cross-context usage; in that
        case this logs a warning and, crucially, does NOT silently replace the
        previous caller binding with ``None`` (no false "restored" claim).
        """
        if self._finished:
            return
        self._finished = True
        token = self._token
        self._token = None
        if token is None:
            return  # never entered, or already consumed
        try:
            _current.reset(token)
        except (ValueError, RuntimeError, TypeError) as exc:
            # Unsupported: the token belongs to a different context/order. Do not
            # overwrite the active binding with None; surface the problem instead.
            logger.warning("RunContext binding could not be restored: %s", exc)

    @classmethod
    def delegate(cls, scope: RunContext):
        """Explicit internal sharing: enter a child that aliases ``scope``'s registry.

        Entering the returned manager keeps ``current()`` as ``scope`` (a share,
        not a new run) and yields the shared child scope, whose ``registry`` is the
        same object. This is how a deliberately shared portion of a run reuses one
        availability state without opening a second run.
        """
        child = cls(delegate=scope)

        class _Share:
            def __enter__(inner):
                # Do not rebind: the shared target stays the active scope.
                return child

            def __exit__(inner, *exc_info):
                child.finish()  # owns no binding; idempotent no-op restore
                return False

        return _Share()


def current() -> RunContext | None:
    """The run scope bound in this execution context, or ``None``."""
    return _current.get()
