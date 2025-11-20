"""Example: Claude Adapter with Structured Generation.

This example demonstrates how to use the Claude adapter's structured_generate
function to get JSON output that matches a specified schema.
"""

import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

from auto_pilot.llm import (
    Message,
    StructuredGenerationParams,
    create_adapter_for_model,
)

# 加载.env文件中的环境变量
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


async def example_basic_structured_output():
    """Example: Basic structured output with Claude."""
    print("=" * 60)
    print("Claude Structured Generation - Basic Example")
    print("=" * 60)

    # Create Claude adapter
    adapter = create_adapter_for_model(model="claude-3-sonnet")

    # Prepare messages
    messages = [
        Message(
            role="system",
            content="You are a data extraction assistant. Extract information exactly as specified.",
        ),
        Message(
            role="user",
            content="Extract the person's details from this text: John Doe is a 30-year-old software engineer working at Tech Corp, earning $120,000 per year.",
        ),
    ]

    # Define JSON schema for the expected output
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "profession": {"type": "string"},
            "company": {"type": "string"},
            "salary": {"type": "number"},
        },
        "required": ["name", "age", "profession"],
    }

    # Create structured generation parameters
    params = StructuredGenerationParams(
        json_schema=schema,
        temperature=0.0,  # Lower temperature for more consistent output
        max_tokens=500,
    )

    # Generate structured response with retry mechanism
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await adapter.structured_generate(
                "claude-3-sonnet", messages, params
            )

            print("\nStructured Response:")
            print(f"Content: {response.content}")

            # Parse and pretty-print the JSON
            try:
                parsed = json.loads(response.content)
                print("\nParsed JSON:")
                print(json.dumps(parsed, indent=2))
                break  # Success, exit retry loop
            except json.JSONDecodeError as e:
                print(f"\nError: Could not parse JSON: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying... (attempt {attempt + 2}/{max_retries})")
                else:
                    print("\nFailed after all retries")

        except Exception as e:
            error_msg = str(e)
            print(f"\nError on attempt {attempt + 1}: {error_msg}")
            if "did not return valid JSON" in error_msg:
                print(
                    "Note: This may be due to MiniMax's limited support for structured generation."
                )
                print("Try running with a different provider or simpler schemas.")
            if attempt < max_retries - 1:
                print(f"Retrying... (attempt {attempt + 2}/{max_retries})")
            else:
                print("\nFailed after all retries")
                raise

    print(f"\nToken usage: {response.usage.total_tokens} total")


async def example_nested_structured_output():
    """Example: Nested structure with arrays and objects."""
    print("\n" + "=" * 60)
    print("Claude Structured Generation - Nested Structure Example")
    print("=" * 60)

    adapter = create_adapter_for_model(model="claude-3-sonnet")

    messages = [
        Message(role="system", content="You extract structured data from text."),
        Message(
            role="user",
            content="Extract project information: Our team has three projects: Project Alpha with 5 members and deadline in Q1, Project Beta with 3 members due in Q2, and Project Gamma with 8 members targeting Q3.",
        ),
    ]

    # Define nested schema
    schema = {
        "type": "object",
        "properties": {
            "project_count": {"type": "integer"},
            "projects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "team_size": {"type": "integer"},
                        "deadline": {"type": "string"},
                    },
                    "required": ["name", "team_size", "deadline"],
                },
            },
        },
        "required": ["project_count", "projects"],
    }

    params = StructuredGenerationParams(
        json_schema=schema,
        temperature=0.0,
        max_tokens=500,
    )

    response = None
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await adapter.structured_generate(
                "claude-3-sonnet", messages, params
            )

            print("\nStructured Response:")
            print(f"Content: {response.content}")

            try:
                parsed = json.loads(response.content)
                print("\nParsed JSON:")
                print(json.dumps(parsed, indent=2))
                break  # Success, exit retry loop
            except json.JSONDecodeError as e:
                print(f"\nError: Could not parse JSON: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying... (attempt {attempt + 2}/{max_retries})")
                else:
                    print("\nFailed after all retries")

        except Exception as e:
            error_msg = str(e)
            print(f"\nError on attempt {attempt + 1}: {error_msg}")
            if "did not return valid JSON" in error_msg:
                print(
                    "Note: This may be due to MiniMax's limited support for structured generation."
                )
                print("Try running with a different provider or simpler schemas.")
            if attempt < max_retries - 1:
                print(f"Retrying... (attempt {attempt + 2}/{max_retries})")
            else:
                print("\nFailed after all retries")
                raise

    if response:
        print(f"\nToken usage: {response.usage.total_tokens} total")


async def example_data_extraction():
    """Example: Complex data extraction with multiple fields."""
    print("\n" + "=" * 60)
    print("Claude Structured Generation - Data Extraction Example")
    print("=" * 60)

    adapter = create_adapter_for_model(model="claude-3-sonnet")

    messages = [
        Message(
            role="system",
            content="You extract structured information from natural language text.",
        ),
        Message(
            role="user",
            content="Extract email campaign details: We're launching a summer sale campaign starting July 15th. We have 50,000 subscribers in our email list. The discount code is SUMMER2024 with 25% off. Expected conversion rate is 5% and we're targeting $150,000 in revenue.",
        ),
    ]

    # Complex schema with multiple types
    schema = {
        "type": "object",
        "properties": {
            "campaign_name": {"type": "string"},
            "start_date": {"type": "string"},
            "subscriber_count": {"type": "integer"},
            "discount_code": {"type": "string"},
            "discount_percentage": {"type": "integer"},
            "expected_conversion_rate": {"type": "number"},
            "revenue_target": {"type": "number"},
            "metrics": {
                "type": "object",
                "properties": {
                    "total_revenue": {"type": "number"},
                    "expected_orders": {"type": "integer"},
                },
            },
        },
        "required": ["campaign_name", "start_date", "discount_code"],
    }

    params = StructuredGenerationParams(
        json_schema=schema,
        temperature=0.1,
        max_tokens=800,
    )

    response = None
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await adapter.structured_generate(
                "claude-3-sonnet", messages, params
            )

            print("\nStructured Response:")
            print(f"Content: {response.content}")

            try:
                parsed = json.loads(response.content)
                print("\nParsed JSON:")
                print(json.dumps(parsed, indent=2))

                # Demonstrate accessing specific fields
                print("\n" + "-" * 60)
                print("Extracted Fields:")
                print(f"  Campaign: {parsed.get('campaign_name')}")
                print(f"  Start Date: {parsed.get('start_date')}")
                print(f"  Subscriber Count: {parsed.get('subscriber_count')}")
                print(
                    f"  Discount: {parsed.get('discount_code')} ({parsed.get('discount_percentage')}%)"
                )
                break  # Success, exit retry loop

            except json.JSONDecodeError as e:
                print(f"\nError: Could not parse JSON: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying... (attempt {attempt + 2}/{max_retries})")
                else:
                    print("\nFailed after all retries")

        except Exception as e:
            error_msg = str(e)
            print(f"\nError on attempt {attempt + 1}: {error_msg}")
            if "did not return valid JSON" in error_msg:
                print(
                    "Note: This may be due to MiniMax's limited support for structured generation."
                )
                print("Try running with a different provider or simpler schemas.")
            if attempt < max_retries - 1:
                print(f"Retrying... (attempt {attempt + 2}/{max_retries})")
            else:
                print("\nFailed after all retries")
                raise

    if response:
        print(f"\nToken usage: {response.usage.total_tokens} total")


async def example_comparison():
    """Example: Compare structured vs unstructured output."""
    print("\n" + "=" * 60)
    print("Claude Structured Generation - Comparison Example")
    print("=" * 60)

    adapter = create_adapter_for_model(model="claude-3-sonnet")

    messages = [
        Message(role="user", content="List the key features of a smartphone."),
    ]

    print("\n--- Unstructured Output ---")
    from auto_pilot.llm import GenerationParams

    unstructured_params = GenerationParams(temperature=0.7, max_tokens=200)
    unstructured_response = await adapter.generate(
        "claude-3-sonnet", messages, unstructured_params
    )
    print(unstructured_response.content)

    print("\n--- Structured Output ---")
    schema = {
        "type": "object",
        "properties": {
            "features": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of smartphone features",
            },
            "category": {
                "type": "string",
                "enum": ["budget", "mid-range", "premium"],
                "description": "Category of the smartphone",
            },
        },
        "required": ["features"],
    }

    structured_params = StructuredGenerationParams(
        json_schema=schema,
        temperature=0.0,
        max_tokens=300,
    )

    structured_response = None
    max_retries = 3
    for attempt in range(max_retries):
        try:
            structured_response = await adapter.structured_generate(
                "claude-3-sonnet", messages, structured_params
            )

            try:
                parsed = json.loads(structured_response.content)
                print(f"Category: {parsed.get('category')}")
                print(f"Features ({len(parsed.get('features', []))} total):")
                for feature in parsed.get("features", []):
                    print(f"  - {feature}")
                break  # Success, exit retry loop

            except json.JSONDecodeError as e:
                print(f"Error: Could not parse JSON: {e}")
                print(f"Raw content: {structured_response.content}")
                if attempt < max_retries - 1:
                    print(f"Retrying... (attempt {attempt + 2}/{max_retries})")
                else:
                    print("\nFailed after all retries")

        except Exception as e:
            error_msg = str(e)
            print(f"\nError on attempt {attempt + 1}: {error_msg}")
            if "did not return valid JSON" in error_msg:
                print(
                    "Note: This may be due to MiniMax's limited support for structured generation."
                )
                print("Try running with a different provider or simpler schemas.")
            if attempt < max_retries - 1:
                print(f"Retrying... (attempt {attempt + 2}/{max_retries})")
            else:
                print("\nFailed after all retries")
                raise

    print(f"\nToken usage (unstructured): {unstructured_response.usage.total_tokens}")
    if structured_response:
        print(f"Token usage (structured): {structured_response.usage.total_tokens}")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Claude Adapter - Structured Generation Examples")
    print("=" * 60)
    print("\nNote: Requires ANTHROPIC_API_KEY to be set")
    print("=" * 60)

    try:
        # Run examples
        await example_basic_structured_output()
        await example_nested_structured_output()
        await example_data_extraction()
        await example_comparison()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        print("\nThis is expected if ANTHROPIC_API_KEY is not configured.")


if __name__ == "__main__":
    asyncio.run(main())
