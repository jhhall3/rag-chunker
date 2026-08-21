from rag_chunker.sentences import split_sentences


def test_empty_text_has_no_sentences():
    assert split_sentences("") == []
    assert split_sentences("   ") == []


def test_text_without_terminal_punctuation_is_one_sentence():
    assert split_sentences("no ending punctuation here") == ["no ending punctuation here"]


def test_splits_on_period_followed_by_space():
    assert split_sentences("First sentence. Second sentence.") == [
        "First sentence.",
        "Second sentence.",
    ]


def test_splits_on_question_and_exclamation_marks():
    assert split_sentences("Is it done? Yes it is!") == ["Is it done?", "Yes it is!"]


def test_does_not_split_on_known_abbreviation():
    assert split_sentences("I emailed Dr. Chen about it.") == [
        "I emailed Dr. Chen about it."
    ]


def test_does_not_split_on_eg_abbreviation():
    text = "See the docs, e.g. the README, for details."
    assert split_sentences(text) == [text]


def test_does_not_split_on_middle_initial():
    text = "Ask J. Smith for the file."
    assert split_sentences(text) == [text]


def test_does_not_split_inside_numbered_list_style_text():
    # "1" and "2" are digits, so the periods after them are not sentence ends.
    text = "Step 1. Step 2."
    assert split_sentences(text) == [text]


def test_keeps_closing_quote_with_the_sentence():
    text = 'She said "stop." Then left.'
    sentences = split_sentences(text)
    assert sentences == ['She said "stop."', "Then left."]
