# Claude + TradingView Readiness - April 9, 2026

## Goal
Keep one clean reference pack ready for the day Claude becomes available for TradingView-facing work.

## Current Webhook Reference Shape
Use the same JSON style already present in webhook-enabled Pine scripts:

```json
{
  "secret": "squeeze_tradingview_cluster_2026_secure",
  "strategy": "Strategy Name",
  "action": "BUY",
  "ticker": "{{ticker}}",
  "interval": "{{interval}}",
  "price": "{{close}}"
}
```

Supported action set currently used in Pine scripts:
- `BUY`
- `SELL`
- `CLOSE_LONG`
- `CLOSE_SHORT`

## Claude Use Cases
1. Draft clean TradingView webhook payloads for new Pine scripts.
2. Explain what a received alert means in strategy terms.
3. Help debug malformed JSON, wrong action labels, or missing fields.
4. Suggest new strategy ideas based on TV result patterns and profitable families.

## Validation Checklist For Claude Access
- Can Claude read and explain the alert JSON correctly?
- Can Claude map `strategy` + `action` to expected trade intent?
- Can Claude detect missing `secret`, invalid `action`, or malformed JSON?
- Can Claude help compare expected alert format vs actual TradingView alert text?
- Can Claude help generate payloads without changing live execution logic?

## Guardrails
- Claude support remains advisory during the paper window.
- No direct execution-path changes from Claude experiments.
- Any new Claude-assisted strategy ideas stay in research only.

## First Test Cases Once Access Opens
1. Valid BUY payload for one webhook-enabled Pine strategy.
2. Invalid payload with missing `secret`.
3. Invalid payload with wrong `action`.
4. Alert text that contains extra whitespace / broken quotes.
5. One “explain this alert” prompt using a real TV fill payload.
