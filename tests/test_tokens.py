from rag_chunker.tokens import estimate_tokens, fits_budget


def test_empty_string_is_zero_tokens():
    assert estimate_tokens("") == 0


def test_short_word_still_costs_one_token():
    # "hi" is 2 chars / 4 = 0.5, but every word costs at least one token.
    assert estimate_tokens("hi") == 1


def test_ascii_word_uses_four_chars_per_token():
    assert estimate_tokens("hello") == 2  # ceil(5 / 4)


def test_digit_run_uses_three_chars_per_token():
    assert estimate_tokens("12345") == 2  # ceil(5 / 3)


def test_short_digit_run_still_costs_one_token():
    assert estimate_tokens("12") == 1


def test_cjk_characters_cost_one_token_each():
    assert estimate_tokens("你好") == 2


def test_newlines_cost_half_a_token_each():
    assert estimate_tokens("\n\n") == 1  # ceil(2 * 0.5)


def test_symbols_cost_more_than_newlines():
    assert estimate_tokens("!!!") == 2  # ceil(3 * 0.6)


def test_spaces_do_not_add_tokens():
    assert estimate_tokens("word") == estimate_tokens("word     ")


def test_whole_string_is_summed_before_rounding():
    # hello (1.25) + world (1.25) = 2.5, ceiling applies once at the end.
    assert estimate_tokens("hello world") == 3


def test_fits_budget_true_when_estimate_at_or_under_budget():
    assert fits_budget("hello world", 3) is True


def test_fits_budget_false_when_estimate_over_budget():
    assert fits_budget("hello world", 2) is False
