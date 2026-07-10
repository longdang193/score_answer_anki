from test_ai_analysis_ui_contract import DummyCard, load_addon_module


def main():
    addon, _mw = load_addon_module()

    assert addon.resolve_slot_field_names(1) == {
        "answer_field": "Back",
        "answer_variants_field": "Back_variants",
        "hint_field": "Hint",
    }
    assert addon.resolve_slot_field_names(2) == {
        "answer_field": "Back2",
        "answer_variants_field": "Back2_variants",
        "hint_field": "Hint2",
    }

    plain_card = DummyCard(model_name="card_1_score", template_name="card_1_score")
    assert addon.get_manual_hint_html(plain_card) == "Base hint"

    cloze_card = DummyCard(model_name="card_1_score_clozeanything1", template_name="card_1_score_clozeanything1")
    cloze_card.note()["Front"] = "This is a |(c1::cat|) and a |(c2::dog|)."
    cloze_card.note()["Back"] = "cat"
    cloze_card.note()["Back_variants"] = ""
    cloze_card.note()["Back2"] = "dog"
    cloze_card.note()["Back2_variants"] = ""
    cloze_card.ord = 1
    assert addon.get_manual_hint_html(cloze_card) == "Second hint"

    del cloze_card.note()["Hint2"]
    cloze_card.note()["Hint"] = "Should not leak"
    assert addon.get_manual_hint_html(cloze_card) == ""

    cloze_card.ord = None
    assert addon.get_manual_hint_html(cloze_card) == ""


if __name__ == "__main__":
    main()
