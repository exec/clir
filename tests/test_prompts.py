"""Tests for prompt functions."""

import pytest

from clir.prompts.input import prompt_input, prompt_confirm, prompt, password, confirm, confirm_password
from clir.prompts.select import select, multiselect
from clir.testing import mock_prompt


class TestPromptInput:
    """Tests for prompt_input function."""

    def test_prompt_returns_input(self):
        """Test that prompt returns user input."""
        with mock_prompt(["hello"]):
            result = prompt("Enter name")
            assert result == "hello"

    def test_prompt_with_default(self):
        """Test that default is used when input is empty."""
        with mock_prompt([""]):
            result = prompt("Enter name", default="world")
            assert result == "world"

    def test_prompt_with_default_uses_input(self):
        """Test that user input overrides default."""
        with mock_prompt(["custom"]):
            result = prompt("Enter name", default="world")
            assert result == "custom"

    def test_prompt_validator_validates(self):
        """Test that validator is called."""
        with mock_prompt(["42"]):
            result = prompt("Enter number", validator=lambda x: int(x) if x.isdigit() else None)
            assert result == 42

    def test_prompt_validator_rejects_invalid(self):
        """Test that validator rejects invalid input."""
        # First input is invalid, second is valid
        with mock_prompt(["abc", "123"]):
            result = prompt("Enter number", validator=lambda x: int(x) if x.isdigit() else None)
            assert result == 123

    def test_prompt_password_masks_input(self):
        """Test that password mode works (doesn't crash)."""
        with mock_prompt(["secret"]):
            result = password("Enter password")
            assert result == "secret"


class TestPromptConfirm:
    """Tests for prompt_confirm function."""

    def test_confirm_yes_response(self):
        """Test that 'y' returns True."""
        with mock_prompt(["y"]):
            result = confirm("Continue?")
            assert result is True

    def test_confirm_yes_full_word(self):
        """Test that 'yes' returns True."""
        with mock_prompt(["yes"]):
            result = confirm("Continue?")
            assert result is True

    def test_confirm_no_response(self):
        """Test that 'n' returns False."""
        with mock_prompt(["n"]):
            result = confirm("Continue?")
            assert result is False

    def test_confirm_empty_with_default_true(self):
        """Test that empty input with default True returns True."""
        with mock_prompt([""]):
            result = confirm("Continue?", default=True)
            assert result is True

    def test_confirm_empty_with_default_false(self):
        """Test that empty input with default False returns False."""
        with mock_prompt([""]):
            result = confirm("Continue?", default=False)
            assert result is False


class TestSelect:
    """Tests for select function."""

    def test_select_returns_choice(self):
        """Test that selecting a valid index returns the choice."""
        with mock_prompt(["1"]):
            result = select(["apple", "banana", "cherry"], "Choose fruit")
            assert result == "apple"

    def test_select_returns_second_choice(self):
        """Test that selecting second choice works."""
        with mock_prompt(["2"]):
            result = select(["apple", "banana", "cherry"], "Choose fruit")
            assert result == "banana"

    def test_select_with_default(self):
        """Test that default is used when input is empty."""
        with mock_prompt([""]):
            result = select(["apple", "banana"], "Choose fruit", default=1)
            assert result == "banana"

    def test_select_validator_transforms(self):
        """Test that validator can transform the result."""
        with mock_prompt(["1"]):
            result = select(
                ["apple", "banana"],
                "Choose fruit",
                validator=lambda x: x.upper()
            )
            assert result == "APPLE"

    def test_select_out_of_range(self):
        """Test that out of range input is handled."""
        # First input is invalid (out of range), second is valid
        with mock_prompt(["99", "1"]):
            result = select(["apple", "banana"], "Choose fruit")
            assert result == "apple"

    def test_select_invalid_input(self):
        """Test that non-numeric input is handled."""
        # First input is invalid, second is valid
        with mock_prompt(["abc", "1"]):
            result = select(["apple", "banana"], "Choose fruit")
            assert result == "apple"


class TestMultiselect:
    """Tests for multiselect function."""

    def test_multiselect_single_choice(self):
        """Test selecting single choice."""
        with mock_prompt(["1"]):
            result = multiselect(["apple", "banana", "cherry"], "Choose fruits")
            assert result == ["apple"]

    def test_multiselect_multiple_choices(self):
        """Test selecting multiple choices."""
        with mock_prompt(["1,3"]):
            result = multiselect(["apple", "banana", "cherry"], "Choose fruits")
            assert result == ["apple", "cherry"]

    def test_multiselect_with_default(self):
        """Test using default selections."""
        with mock_prompt([""]):
            result = multiselect(
                ["apple", "banana", "cherry"],
                "Choose fruits",
                default=[0, 2]
            )
            assert result == ["apple", "cherry"]

    def test_multiselect_invalid_index(self):
        """Test that invalid indices are handled gracefully."""
        # Invalid index 99 is ignored
        with mock_prompt(["1,99,2"]):
            result = multiselect(["apple", "banana", "cherry"], "Choose fruits")
            assert result == ["apple", "banana"]

    def test_multiselect_empty_input(self):
        """Test that empty input returns empty list."""
        with mock_prompt([""]):
            result = multiselect(["apple", "banana"], "Choose fruits")
            assert result == []

    def test_multiselect_invalid_format(self):
        """Test that invalid format is handled."""
        # Invalid format, then valid
        with mock_prompt(["abc", "1,2"]):
            result = multiselect(["apple", "banana"], "Choose fruits")
            assert result == ["apple", "banana"]


class TestEdgeCases:
    """Edge case tests for prompts."""

    def test_select_empty_choices_raises(self):
        """Test that empty choices list raises an error."""
        with pytest.raises((ValueError, IndexError)):
            select([], "Choose something")

    def test_prompt_unicode_input(self):
        """Test that unicode input works."""
        with mock_prompt(["hello world"]):
            result = prompt("Say hello")
            assert result == "hello world"

    def test_select_unicode_choices(self):
        """Test that unicode choices work."""
        with mock_prompt(["1"]):
            result = select(["apple", "banana", "café"], "Choose")
            assert result == "apple"


class TestConfirmPassword:
    """Tests for confirm_password function."""

    def test_confirm_password_matching(self):
        """Test that matching passwords are accepted."""
        with mock_prompt(["secret", "secret"]):
            result = confirm_password("Password")
            assert result == "secret"

    def test_confirm_password_mismatch_then_match(self):
        """Test that mismatched passwords are rejected then accepted."""
        with mock_prompt(["first", "second", "third", "third"]):
            result = confirm_password("Password")
            assert result == "third"

    def test_confirm_password_mismatched(self):
        """Test that mismatched passwords require retry."""
        with mock_prompt(["wrong", "right", "secret", "secret"]):
            result = confirm_password("Password")
            assert result == "secret"

    def test_confirm_password_min_length_valid(self):
        """Test password meets minimum length."""
        with mock_prompt(["password123", "password123"]):
            result = confirm_password("Password", min_length=8)
            assert result == "password123"

    def test_confirm_password_min_length_rejected(self):
        """Test password below minimum length is rejected."""
        with mock_prompt(["short", "short", "longerpassword", "longerpassword"]):
            result = confirm_password("Password", min_length=8)
            assert result == "longerpassword"

    def test_confirm_password_min_length(self):
        """Test that min_length is enforced."""
        with mock_prompt(["abc", "password", "password"]):
            result = confirm_password("Password", min_length=5)
            assert result == "password"
