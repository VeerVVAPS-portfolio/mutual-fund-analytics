"""
TrueSIP shared/ package.

Self-contained finance primitives promoted from Projects 1/2/6.
Import everything downstream agents and the dashboard need from here —
no runtime imports from sibling project folders.

Public surface:
  from shared.scoring      import apply_eligibility_filter, compute_composite_score, WEIGHTS, AUM_THRESHOLD_CR
  from shared.metrics      import cagr, compute_fund_metrics  (pure math; no file I/O)
  from shared.risk_profiler import compute_risk_score, get_risk_label, get_base_allocation,
                                    score_to_gauge_color, QUESTIONS, BASE_ALLOCATIONS,
                                    horizon_equity_band
  from shared.goal_calculator import solve_goal, GoalResult, future_value_required,
                                      required_fixed_sip, required_stepup_sip
  from shared.cashflow_projection import project_cashflow, ProjectionYear
  from shared.planning_engine import (build_plan, RETURN_ASSUMPTIONS, horizon_band,
                                      reconcile_allocation, blended_expected_return,
                                      split_sip_by_asset, equity_category_for)
  from shared.protection   import (recommended_life_cover, recommended_health_cover,
                                    recommended_emergency_fund, compute_foir,
                                    outstanding_loan_balance)
  from shared.data_store   import load_scored_funds
  from shared.theme        import inject_theme
"""
