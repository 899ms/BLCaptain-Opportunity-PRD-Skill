#!/usr/bin/env python3
"""Mock model CLI for P1 health-check tests."""

import sys


prompt = sys.stdin.read().strip() or "ping"
print(f"mock-model-ok: {prompt[:40]}")
