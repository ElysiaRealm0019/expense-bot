#!/usr/bin/env python3
"""
All Models Cost Extractor

Extract actual API costs from OpenClaw session JSONL files.
Shows costs grouped by model, applying different pricing rules:
- MiniMax: £5/month fixed (unlimited)
- Other models: actual API costs from JSONL

Usage:
    python3 extract-cost.py [options]
"""

import json
import re
import os
import sys
import glob
from collections import defaultdict
from datetime import datetime

SESSIONS_DIR = os.path.expanduser("~/.openclaw/agents/main/sessions")

# Pricing configuration
PRICING = {
    "minimax": {
        "monthly_fixed_gbp": 5.00,  # £5/month unlimited
        "models": ["MiniMax-M2.1", "minimax/MiniMax-M2.1", "minimax/minimax/MiniMax-M2.1"]
    },
    "google": {
        "currency": "USD",
        "note": "Actual costs from API",
        "models": ["gemini-1.0", "gemini-1.5", "gemini-2.0", "gemini-2.5", "gemini-3.0"]
    },
}

# Models that use fixed monthly pricing
FIXED_PRICE_MODELS = {
    "MiniMax-M2.1",
    "minimax/MiniMax-M2.1",
    "minimax/minimax/MiniMax-M2.1"
}

# Model name normalization (merge duplicates)
MODEL_ALIASES = {
    "google/gemini-2.5-flash": "gemini-2.5-flash",
    "google/gemini-3-flash-preview": "gemini-3-flash-preview",
    "google/gemini-3-pro-preview": "gemini-3-pro-preview",
    "google/gemini-2.0-flash": "gemini-2.0-flash",
    "google/gemini-2.0-pro": "gemini-2.0-pro",
    "google/gemini-2.5-pro": "gemini-2.5-pro",
}

def extract_from_jsonl():
    """Extract costs from JSONL files"""
    daily_costs = defaultdict(float)  # {date: total_cost}
    model_costs = defaultdict(float)  # {model: total_cost}
    used_models = set()  # Track which models were actually used

    pattern = re.compile(r'"timestamp":"([^"]+)".*?"total":([0-9.]+)')

    for filepath in glob.glob(os.path.join(SESSIONS_DIR, "*.jsonl")):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    match = pattern.search(line)
                    if match:
                        timestamp = match.group(1)
                        cost = float(match.group(2))
                        date = timestamp.split('T')[0]

                        # Extract model info
                        model_match = re.search(r'"model":"([^"]+)"', line)

                        if model_match:
                            model = model_match.group(1)
                            # Normalize model names (merge duplicates)
                            if model in MODEL_ALIASES:
                                model = MODEL_ALIASES[model]
                            used_models.add(model)
                        else:
                            model = "unknown"

                        if cost > 0.0001:
                            daily_costs[date] += cost
                            model_costs[model] += cost

        except Exception:
            continue

    return dict(daily_costs), dict(model_costs), used_models

def apply_pricing_rules(model_costs, used_models):
    """Apply different pricing rules per model"""
    result = defaultdict(float)
    summary = {}

    monthly_fixed_used = False

    for model, cost in model_costs.items():
        if model in FIXED_PRICE_MODELS:
            # Check if MiniMax was actually used (has non-zero cost in any session)
            if cost > 0 or model in used_models:
                # Apply monthly fixed price
                result["MiniMax (Fixed £5/mo)"] = 5.00
                monthly_fixed_used = True
                summary[model] = {
                    "actual_cost": cost,
                    "billed": 5.00,
                    "type": "fixed_monthly",
                    "currency": "GBP"
                }
        else:
            # Use actual API costs (USD usually)
            result[model] = cost
            summary[model] = {
                "actual_cost": cost,
                "billed": cost,
                "type": "api_usage",
                "currency": "USD"
            }

    return dict(result), summary, monthly_fixed_used

def filter_by_date(daily_costs, date_filter):
    """Filter by date range"""
    if not date_filter:
        return daily_costs

    result = {}
    if date_filter.startswith("week:"):
        start_date = date_filter[5:]
        for date, cost in daily_costs.items():
            if date >= start_date:
                result[date] = cost
    elif date_filter.startswith("month:"):
        month = date_filter[6:]
        for date, cost in daily_costs.items():
            if date.startswith(month):
                result[date] = cost
    else:
        if date_filter in daily_costs:
            result[date_filter] = daily_costs[date_filter]

    return result

def main():
    args = sys.argv[1:]
    
    output_format = "text"
    date_filter = ""
    by_model = False
    yesterday_mode = False

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--yesterday":
            yesterday = datetime.now()
            from datetime import timedelta
            yesterday -= timedelta(days=1)
            date_filter = yesterday.strftime("%Y-%m-%d")
            yesterday_mode = True
        elif arg == "--date" and i + 1 < len(args):
            date_filter = args[i + 1]
            i += 1
        elif arg == "--week":
            from datetime import timedelta
            week_ago = datetime.now() - timedelta(days=7)
            date_filter = f"week:{week_ago.strftime('%Y-%m-%d')}"
        elif arg == "--month":
            date_filter = f"month:{datetime.now().strftime('%Y-%m')}"
        elif arg == "--by-model":
            by_model = True
        elif arg == "--json":
            output_format = "json"
        i += 1

    raw_daily, raw_model, used_models = extract_from_jsonl()
    
    # Apply pricing rules
    billed_costs, pricing_summary, has_fixed = apply_pricing_rules(raw_model, used_models)
    
    # Filter by date
    filtered_daily = filter_by_date(raw_daily, date_filter)

    # Calculate totals
    if yesterday_mode or date_filter and not date_filter.startswith("week:") and not date_filter.startswith("month:"):
        # Single day mode: only count costs for that specific day
        single_day = date_filter
        # Recalculate model costs for just that day
        single_day_model_costs = defaultdict(float)
        pattern = re.compile(r'"timestamp":"([^"]+)".*?"total":([0-9.]+)')
        
        for filepath in glob.glob(os.path.join(SESSIONS_DIR, "*.jsonl")):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        match = pattern.search(line)
                        if match:
                            timestamp = match.group(1)
                            cost = float(match.group(2))
                            date = timestamp.split('T')[0]
                            if date == single_day and cost > 0.0001:
                                model_match = re.search(r'"model":"([^"]+)"', line)
                                if model_match:
                                    model = model_match.group(1)
                                    if model in MODEL_ALIASES:
                                        model = MODEL_ALIASES[model]
                                    single_day_model_costs[model] += cost
            except Exception:
                continue
        
        # Apply pricing rules to single day
        pricing_result = apply_pricing_rules(dict(single_day_model_costs), used_models)
        day_billed = pricing_result[0]
        day_has_fixed = pricing_result[2]
        # For single day, calculate USD total from non-fixed-price models
        total_usd = 0
        for model, cost in single_day_model_costs.items():
            # Skip MiniMax variants (they use fixed pricing)
            if "MiniMax" in model or "minimax" in model:
                continue
            total_usd += cost
        total_gbp = 5.00 if day_has_fixed else 0
        sorted_billed = sorted(day_billed.items(), key=lambda x: -x[1])
    else:
        # Multi-day mode
        total_usd = sum(cost for model, cost in billed_costs.items() if "MiniMax" not in model)
        total_gbp = 5.00 if has_fixed else 0
        sorted_billed = sorted(billed_costs.items(), key=lambda x: -x[1])

    # Sort by cost
    sorted_daily = sorted(filtered_daily.items())

    if output_format == "json":
        result = {
            "generatedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pricingRules": {
                "MiniMax": "£5/month fixed (unlimited)",
                "Others": "Actual API costs (USD)"
            },
            "byModel": dict(sorted_billed),
            "byDate": dict(sorted_daily),
            "summary": {
                "totalGBP": total_gbp,
                "totalUSD": round(total_usd, 2)
            }
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("=" * 55)
        print("💰 AI API Cost Report")
        print("=" * 55)
        print()
        
        print("📊 Pricing Rules Applied:")
        print("   • MiniMax: £5/month fixed (unlimited)")
        print("   • Others:  Actual API costs (USD)")
        print()
        
        if by_model:
            print("📈 Costs by Model:")
            print("-" * 55)
            for model, cost in sorted_billed:
                if "MiniMax" in model:
                    print(f"   {model:35} £{cost:.2f}/mo")
                else:
                    print(f"   {model:35} ${cost:.4f}")
            print()
            print("-" * 55)
            print(f"   {'TOTAL':35} £{total_gbp:.2f} + ${total_usd:.2f} USD")
        else:
            print("📅 Daily Costs:")
            print("-" * 55)
            for date, cost in sorted_daily:
                print(f"   {date}  ${cost:.4f}")
            print()
            print("-" * 55)
            print(f"   {'TOTAL':13} £{total_gbp:.2f} + ${total_usd:.2f} USD")
        
        print()
        print("=" * 55)

if __name__ == "__main__":
    main()
