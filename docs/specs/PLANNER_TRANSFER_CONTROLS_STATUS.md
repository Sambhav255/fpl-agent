# Planner transfer controls

The planner supports explicit per-event transfer caps, a separate weekly candidate, saved weekly plans, eligible chip timing comparisons, and selling-price confirmation. Normal analysis resets special-chip policy; chip analysis remains explicit. Search is bounded and does not claim a globally optimal strategy.

Unknown selling prices remain unknown until explicitly accepted or corrected. Accepting an estimated selling price does not set a purchase price. Public imports preserve the distinction between deadline picks and private current state.

Synthetic browser tests cover one- and three-transfer requests through the worker and persisted weekly plans on desktop and mobile. Backend tests cover zero/one-transfer limits, best single candidates, and marginal chip value. Optional live verification checks the unconfirmed-price gate without changing private financial values or executing FPL actions.

Real transfer recommendations remain blocked whenever required financial state is unconfirmed. High-level ML forecasts remain inactive pending the release requirements in [ML integration](ML_INTEGRATION.md).
