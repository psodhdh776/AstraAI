import pytest
from modules.i18n import I18n, t, set_lang, get_i18n


class TestI18n:
    def test_default_lang(self):
        i = I18n()
        assert i.lang == "ru"

    def test_invalid_lang_falls_back_to_ru(self):
        i = I18n("invalid")
        assert i.lang == "ru"

    def test_de_lang(self):
        i = I18n("de")
        assert i.lang == "de"

    def test_fr_lang(self):
        i = I18n("fr")
        assert i.lang == "fr"

    def test_t_known_key(self):
        i = I18n("en")
        assert i.t("app_name") == "Astra AI"
        assert i.t("send") == "Send"

    def test_t_unknown_key_returns_key(self):
        i = I18n("en")
        assert i.t("nonexistent_key") == "nonexistent_key"

    def test_t_with_args(self):
        i = I18n("ru")
        assert i.t("reminder_set") == "Напомню через"

    def test_set_lang(self):
        i = I18n("ru")
        i.set_lang("en")
        assert i.lang == "en"
        assert i.t("chat") == "Chat"

    def test_set_lang_invalid(self):
        i = I18n("ru")
        i.set_lang("invalid")
        assert i.lang == "ru"

    def test_weekday(self):
        i = I18n("ru")
        assert i.weekday(0) == "понедельник"
        assert i.weekday(6) == "воскресенье"

    def test_weekday_out_of_range(self):
        i = I18n("ru")
        assert i.weekday(7) == ""

    def test_month(self):
        i = I18n("en")
        assert i.month(1) == "January"
        assert i.month(12) == "December"

    def test_month_out_of_range(self):
        i = I18n("ru")
        assert i.month(0) == ""
        assert i.month(13) == ""

    def test_global_t(self):
        old = get_i18n().lang
        set_lang("en")
        assert t("chat") == "Chat"
        set_lang(old)

    def test_global_set_lang(self):
        old = get_i18n().lang
        set_lang("fr")
        assert get_i18n().lang == "fr"
        set_lang(old)

    def test_ru_translations(self):
        i = I18n("ru")
        assert i.t("welcome") is not None
        assert i.t("exit_message") is not None
        assert len(i._strings.get("weekdays", [])) == 7

    @pytest.mark.parametrize("lang", ["ru", "en", "de", "fr"])
    def test_all_langs_have_all_keys(self, lang):
        i = I18n(lang)
        keys = ["app_name", "chat", "send", "welcome", "exit_message",
                "weekdays", "months", "settings", "save", "cancel"]
        for k in keys:
            val = i.t(k)
            assert val is not None, f"Missing key '{k}' in {lang}"
