#!/usr/bin/env python3
"""
Test runner for the Tool System module.

This script runs all tests for the new modular tool system.
"""

import sys

import pytest


def main():
    """Run all tool system tests."""
    print("=" * 60)
    print("AutoPilot Tool System Tests")
    print("=" * 60)

    # Run tests with verbose output
    args = [
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
    ]

    # Add coverage if requested
    if "--cov" in sys.argv:
        args.extend(
            [
                "--cov=auto_pilot.tools",
                "--cov-report=term-missing",
                "--cov-report=html",
            ]
        )

    # Add coverage threshold if requested
    if "--cov-min" in sys.argv:
        args.append("--cov-fail-under=90")

    exit_code = pytest.main(args + ["tests/test_tools/"])

    if exit_code == 0:
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Some tests failed")
        print("=" * 60)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
