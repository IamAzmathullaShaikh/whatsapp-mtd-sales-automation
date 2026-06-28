import numpy as np

def get_brand_status(target, actual):
    """Evaluates granular brand level metrics, balances, and traffic light thresholds."""
    balance = max(0, target - actual)
    pct = (actual * 100.0 / target) if target > 0 else 100.0
    
    if pct >= 90.0:
        light = "🟢"
    elif pct >= 70.0:
        light = "🟡"
    else:
        light = "🔴"
        
    return light, round(pct, 1), balance

def get_pacing_recommendation(total_ach_pct, expected_shortfall):
    """Generates automated actionable insights based on shortfall trends."""
    if expected_shortfall > 250:
        return "🚨 CRITICAL SHORTFALL EXPECTED: Urgent stock lifting push required immediately."
    elif expected_shortfall > 100:
        return "⚠️ PACING BEHIND TARGET: Step up secondary sales activities to fill the gap."
    elif total_ach_pct >= 95.0:
        return "🟢 ON TRACK: Excellent velocity. Maintain current run rate to lock in slab incentives."
    else:
        return "📋 STABLE PACE: Continuous daily monitoring required to prevent drop-offs."
