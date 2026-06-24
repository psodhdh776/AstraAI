import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import pytest
from unittest.mock import MagicMock


class TestVoiceCommands:
    def test_voice_commands_dict(self):
        from voice_engine import VOICE_COMMANDS
        assert "чат" in VOICE_COMMANDS
        assert "заметки" in VOICE_COMMANDS
        assert "стоп" in VOICE_COMMANDS
        assert "помощь" in VOICE_COMMANDS

    def test_voice_commands_structure(self):
        from voice_engine import VOICE_COMMANDS
        for cmd, (action, tab_idx) in VOICE_COMMANDS.items():
            assert isinstance(action, str)
            assert tab_idx is None or isinstance(tab_idx, int)


class TestVoiceEngine:
    def setup_method(self):
        from voice_engine import VoiceEngine
        self.asst = MagicMock()
        self.asst.listening = False
        self.ve = VoiceEngine(self.asst)

    def test_init(self):
        assert self.ve.assistant is not None
        assert not self.ve.listening

    def test_match_command_chat(self):
        assert self.ve._match_command("открой чат") == "chat"

    def test_match_command_notes(self):
        assert self.ve._match_command("покажи заметки") == "notes"

    def test_match_command_help(self):
        assert self.ve._match_command("помощь") == "help"

    def test_match_command_screenshot(self):
        assert self.ve._match_command("сделай скриншот") == "screenshot"

    def test_match_command_quit(self):
        assert self.ve._match_command("выйти") == "quit"

    def test_match_command_stop(self):
        assert self.ve._match_command("стоп") == "stop"

    def test_match_command_silent(self):
        assert self.ve._match_command("тихо") == "silent"

    def test_match_command_none(self):
        assert self.ve._match_command("неизвестная команда") is None

    def test_get_action_data_chat(self):
        data = self.ve.get_action_data("chat")
        assert data["tab_index"] == 1

    def test_get_action_data_quit(self):
        data = self.ve.get_action_data("quit")
        assert data["tab_index"] is None

    def test_get_action_data_unknown(self):
        data = self.ve.get_action_data("unknown_action")
        assert data["tab_index"] is None

    def test_handle_text_wake_word(self):
        self.ve._wake_word = "астра"
        cb = MagicMock()
        self.ve._callback = cb
        self.ve._handle_text("астра привет")
        assert cb.called

    def test_handle_text_no_wake_word(self):
        self.ve._wake_word = "астра"
        cb = MagicMock()
        self.ve._callback = cb
        self.ve._handle_text("просто привет")
        assert not cb.called

    def test_handle_text_only_wake_word(self):
        self.ve._wake_word = "астра"
        cb = MagicMock()
        self.ve._callback = cb
        self.ve._handle_text("астра")
        assert not cb.called

    def test_start_no_model(self):
        self.ve._model = None
        self.ve._recognizer = None
        result = self.ve.start(callback=lambda x: None)
        assert not result
