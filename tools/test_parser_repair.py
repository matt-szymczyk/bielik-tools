"""Unit tests for Bielik tool parser JSON repair functionality."""
import pytest
import json
from json_repair import repair_json
from bielik_vllm_tool_parser import split_multiple_tool_calls


class TestSplitMultipleToolCalls:
    """Tests for splitting multiple tool calls in one tag."""

    def test_single_call(self):
        """Single tool call should return list with one element."""
        input_str = '{"name": "pods_list", "arguments": {"namespace": "test"}}'
        result = split_multiple_tool_calls(input_str)
        assert len(result) == 1
        assert json.loads(result[0])["name"] == "pods_list"

    def test_two_calls(self):
        """Two tool calls should be split correctly."""
        input_str = '{"name": "A", "arguments": {}}, {"name": "B", "arguments": {}}'
        result = split_multiple_tool_calls(input_str)
        assert len(result) == 2
        assert json.loads(result[0])["name"] == "A"
        assert json.loads(result[1])["name"] == "B"

    def test_three_calls(self):
        """Three tool calls should be split correctly."""
        input_str = '{"name": "A"}, {"name": "B"}, {"name": "C"}'
        result = split_multiple_tool_calls(input_str)
        assert len(result) == 3

    def test_with_whitespace(self):
        """Whitespace between calls should be handled."""
        input_str = '{"name": "A"}  ,  {"name": "B"}'
        result = split_multiple_tool_calls(input_str)
        assert len(result) == 2

    def test_nested_objects(self):
        """Nested objects should not be incorrectly split."""
        input_str = '{"name": "test", "arguments": {"nested": {"key": "value"}}}'
        result = split_multiple_tool_calls(input_str)
        assert len(result) == 1
        parsed = json.loads(result[0])
        assert parsed["arguments"]["nested"]["key"] == "value"


class TestJsonRepair:
    """Tests for json-repair library with Bielik-specific cases."""

    def test_unquoted_keys(self):
        """Unquoted keys should be fixed."""
        result = repair_json('{name: "test", arguments: {}}')
        parsed = json.loads(result) if isinstance(result, str) else result
        assert parsed["name"] == "test"

    def test_trailing_comma(self):
        """Trailing commas should be removed."""
        result = repair_json('{"name": "test",}')
        parsed = json.loads(result) if isinstance(result, str) else result
        assert parsed["name"] == "test"

    def test_missing_closing_brace(self):
        """Missing closing brace should be added."""
        result = repair_json('{"name": "test", "arguments": {"a": 1}')
        parsed = json.loads(result) if isinstance(result, str) else result
        assert parsed["name"] == "test"

    def test_single_quotes(self):
        """Single quotes should be converted to double quotes."""
        result = repair_json("{'name': 'test'}")
        parsed = json.loads(result) if isinstance(result, str) else result
        assert parsed["name"] == "test"

    def test_real_bielik_output_unquoted(self):
        """Real Bielik output with unquoted keys should be fixed."""
        bielik_output = '''{name: "pods_list_in_namespace", arguments: {namespace: "benchmark-t01"}}'''
        result = repair_json(bielik_output)
        parsed = json.loads(result) if isinstance(result, str) else result
        assert parsed["name"] == "pods_list_in_namespace"
        assert parsed["arguments"]["namespace"] == "benchmark-t01"

    def test_real_bielik_output_mixed(self):
        """Real Bielik output with mixed issues should be fixed."""
        bielik_output = '''{name: "events_list", arguments: {namespace: "benchmark-t01", limit: 10,}}'''
        result = repair_json(bielik_output)
        parsed = json.loads(result) if isinstance(result, str) else result
        assert parsed["name"] == "events_list"
        assert parsed["arguments"]["namespace"] == "benchmark-t01"
        assert parsed["arguments"]["limit"] == 10


class TestIntegration:
    """Integration tests combining split and repair."""

    def test_multiple_malformed_calls(self):
        """Multiple malformed calls should all be fixed."""
        input_str = '{name: "A", arguments: {}}, {name: "B", arguments: {x: 1}}'
        parts = split_multiple_tool_calls(input_str)
        assert len(parts) == 2

        for part in parts:
            result = repair_json(part)
            parsed = json.loads(result) if isinstance(result, str) else result
            assert "name" in parsed
            assert "arguments" in parsed

    def test_complex_bielik_output(self):
        """Complex Bielik output from benchmark should be handled."""
        # This is a simplified version of real problematic output
        bielik_output = '''{name: "pods_get", arguments: {name: "webapp-backend-xyz", namespace: "benchmark-t01"}}, {name: "pods_log", arguments: {name: "webapp-backend-xyz", namespace: "benchmark-t01", tail: 30}}'''

        parts = split_multiple_tool_calls(bielik_output)
        assert len(parts) == 2

        results = []
        for part in parts:
            repaired = repair_json(part)
            parsed = json.loads(repaired) if isinstance(repaired, str) else repaired
            results.append(parsed)

        assert results[0]["name"] == "pods_get"
        assert results[1]["name"] == "pods_log"
        assert results[1]["arguments"]["tail"] == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
