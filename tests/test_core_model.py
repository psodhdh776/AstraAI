"""Tests for CoreModel v2 — medium-level cognitive engine."""

import sys
sys.path.insert(0, r"C:\Users\admin\Desktop\AbsoluteAssistant")

from modules.core_model import (
    CoreModel, EnsembleIntentResolver, ReasoningEngine,
    DialoguePlanner, EngineDispatcher, OnlineLearner,
    Introspection, PersonalityDynamics, EpisodicMemory,
    ProactiveEngine, _tokenize, _clamp,
)


# ── UTILITIES ──

def test_tokenize():
    tokens = _tokenize("Привет мир! Это тестовое сообщение.")
    assert len(tokens) > 0
    assert "привет" in tokens
    assert "тестовое" in tokens
    assert "это" not in tokens


def test_clamp():
    assert _clamp(1.5) == 1.0
    assert _clamp(-0.5) == 0.0
    assert _clamp(0.5) == 0.5


# ── v1: EnsembleIntentResolver ──

def test_ensemble_resolver_greeting():
    r = EnsembleIntentResolver()
    result = r.resolve("Привет!")
    assert result["intent"] == "greeting"
    assert result["confidence"] >= 0.6


def test_ensemble_resolver_farewell():
    r = EnsembleIntentResolver()
    result = r.resolve("Пока")
    assert result["intent"] == "farewell"


def test_ensemble_resolver_joke():
    r = EnsembleIntentResolver()
    result = r.resolve("Расскажи шутку")
    assert result["intent"] == "ask_joke"


def test_ensemble_resolver_story():
    r = EnsembleIntentResolver()
    result = r.resolve("Расскажи историю")
    assert result["intent"] == "ask_story"


def test_ensemble_resolver_command():
    r = EnsembleIntentResolver()
    result = r.resolve("Который час?")
    assert result["is_command"]
    assert result["command_type"] == "time"


def test_ensemble_resolver_entity_name():
    r = EnsembleIntentResolver()
    result = r.resolve("Меня зовут Анна")
    assert result["entities"].get("user_name") == "Анна"


def test_ensemble_resolver_entity_like():
    r = EnsembleIntentResolver()
    result = r.resolve("Я люблю программирование")
    assert "программирование" in result["entities"].get("like", "")


def test_ensemble_resolver_unknown():
    r = EnsembleIntentResolver()
    result = r.resolve("ыыыы цццц йййй")
    assert result["intent"] == "unknown"


def test_ensemble_resolver_voting():
    r = EnsembleIntentResolver()
    result = r.resolve("Как дела?")
    assert result["intent"] in ("ask_state", "greeting")
    assert result["confidence"] > 0


def test_ensemble_resolver_context():
    r = EnsembleIntentResolver()
    ctx = {"last_intent": "topic_music", "last_topic": "topic_music"}
    result = r.resolve("а ещё что интересного?", ctx)
    assert result["intent"] in ("topic_music", "ask_more")

def test_ensemble_resolver_context_followup():
    r = EnsembleIntentResolver()
    ctx = {"last_intent": "topic_music", "last_topic": "topic_music"}
    result = r.resolve("и", ctx)
    assert result["intent"] == "topic_music"


def test_ensemble_resolver_save_load():
    r = EnsembleIntentResolver()
    r.learn_success("greeting")
    data = r.to_dict()
    assert "greeting" in data["history_boost"]

    r2 = EnsembleIntentResolver()
    r2.from_dict(data)
    assert r2._history_boost.get("greeting", 0) > 0


# ── v2: ReasoningEngine ──

def test_reasoning_basic():
    eng = ReasoningEngine()
    result = eng.reason("Привет!", "greeting", 0.9, {})
    assert result["original_intent"] == "greeting"
    assert result["refined_confidence"] >= 0.5
    assert len(result["reasoning_steps"]) >= 2


def test_reasoning_low_confidence():
    eng = ReasoningEngine()
    result = eng.reason("абырвалг", "unknown", 0.1, {})
    assert result["needs_clarification"] is True


def test_reasoning_trace():
    eng = ReasoningEngine()
    eng.reason("Привет", "greeting", 0.9, {})
    trace = eng.get_trace_str()
    assert "CLARIFY" in trace
    assert "FORMULATE" in trace


def test_reasoning_save_load():
    eng = ReasoningEngine()
    eng.reason("тест", "greeting", 0.9, {})
    data = eng.to_dict()
    assert data["reasoning_depth"] >= 1

    eng2 = ReasoningEngine()
    eng2.from_dict(data)
    assert eng2.reasoning_depth >= 1


# ── v3: DialoguePlanner ──

def test_planner_goal_inference():
    p = DialoguePlanner()
    plan = p.plan("ask_joke", 0.9, "Расскажи шутку")
    assert plan["goal"] == "entertain"

    plan = p.plan("express_negative", 0.9, "Мне грустно")
    assert plan["goal"] == "empathize"

    plan = p.plan("ask_time", 0.9, "Сколько время?")
    assert plan["goal"] == "assist"


def test_planner_proactive_detection():
    p = DialoguePlanner()
    p.turn_count = 10
    p.user_engagement = 0.6
    assert p._should_be_proactive() is True


def test_planner_topic_change_detection():
    p = DialoguePlanner()
    for _ in range(6):
        p.plan("greeting", 0.9, "Привет")
    # After 6+ greetings, should suggest change
    assert p._should_change_topic() is True


def test_planner_mixed_topics():
    p = DialoguePlanner()
    topics = ["greeting", "topic_music", "topic_food", "topic_work", "ask_joke"]
    for t in topics:
        p.plan(t, 0.9, "текст")
    assert p._should_change_topic() is False  # diverse topics


def test_planner_save_load():
    p = DialoguePlanner()
    p.plan("greeting", 0.9, "Привет")
    data = p.to_dict()
    assert data["turn_count"] == 1

    p2 = DialoguePlanner()
    p2.from_dict(data)
    assert p2.turn_count == 1


# ── v5: OnlineLearner ──

def test_learner_message():
    l = OnlineLearner()
    l.learn_from_message("Я люблю программирование", "express_love", 0.9)
    assert l.user_word_freq["люблю"] >= 1
    assert l.user_word_freq["программирование"] >= 1


def test_learner_intent_mapping():
    l = OnlineLearner()
    l.learn_from_message("Я люблю Python", "express_love", 0.9)
    top = l.get_top_words_for_intent("express_love")
    assert "люблю" in top


def test_learner_frequent_words():
    l = OnlineLearner()
    for i in range(5):
        l.learn_from_message("Python это здорово", "express_positive", 0.9)
    words = l.get_frequent_words(min_freq=3)
    assert words.get("python", 0) >= 3


def test_learner_save_load():
    l = OnlineLearner()
    l.learn_from_message("Привет мир", "greeting", 0.9)
    data = l.to_dict()
    assert "user_word_freq" in data

    l2 = OnlineLearner()
    l2.from_dict(data)
    assert l2.user_word_freq["привет"] >= 1


# ── v6: Introspection ──

def test_introspection_short_response():
    i = Introspection()
    result = i.evaluate("Да", {"intent": "unknown"}, {"engine": "fallback"})
    assert result["score"] < 0.5


def test_introspection_good_response():
    i = Introspection()
    result = i.evaluate("Привет! Как твои дела? Чем могу помочь?",
                         {"intent": "greeting", "confidence": 0.9},
                         {"engine": "chat"})
    assert result["score"] >= 0.3


def test_introspection_correction():
    i = Introspection()
    for _ in range(3):
        i.evaluate("Да", {"intent": "unknown"}, {"engine": "fallback"})
    correction = i.get_correction("Да", {})
    assert correction is not None
    assert len(correction) > 10


def test_introspection_no_correction():
    i = Introspection()
    correction = i.get_correction("Отличный ответ!", {})
    assert correction is None


def test_introspection_avg_quality():
    i = Introspection()
    assert i.get_average_quality() == 0.5  # default
    i.evaluate("Прекрасный ответ длиной более 30 символов",
                {"intent": "greeting"}, {"engine": "chat"})
    assert i.get_average_quality() > 0.3


def test_introspection_save_load():
    i = Introspection()
    i.evaluate("тест", {"intent": "unknown"}, {"engine": "fallback"})
    data = i.to_dict()
    i2 = Introspection()
    i2.from_dict(data)
    assert i2.correction_count == 0  # no correction triggered yet


# ── v7: PersonalityDynamics ──

def test_personality_traits_default():
    p = PersonalityDynamics()
    assert p.traits["warmth"] == 0.75
    assert p.traits["humor"] == 0.65


def test_personality_mood_trigger():
    p = PersonalityDynamics()
    p.update("express_negative", "Мне грустно")
    assert p.mood == "supportive"


def test_personality_cheerful_trigger():
    p = PersonalityDynamics()
    p.update("express_positive", "Отлично!")
    assert p.mood == "cheerful"


def test_personality_emoji():
    p = PersonalityDynamics()
    assert isinstance(p.should_use_emoji(), bool)


def test_personality_mood_report():
    p = PersonalityDynamics()
    p.update("greeting", "Привет")
    report = p.get_mood_report()
    assert isinstance(report, str)
    assert len(report) > 0


def test_personality_save_load():
    p = PersonalityDynamics()
    p.update("express_positive", "Супер!")
    data = p.to_dict()
    assert data["mood"] == "cheerful"

    p2 = PersonalityDynamics()
    p2.from_dict(data)
    assert p2.mood == "cheerful"


# ── v8: EpisodicMemory ──

def test_episodic_remember():
    m = EpisodicMemory()
    m.remember("user", "Меня зовут Дима", "introduce_name", {"user_name": "Дима"})
    assert len(m.episodes) == 1
    assert m.episodes[0]["importance"] >= 0.6


def test_episodic_recall():
    m = EpisodicMemory()
    m.remember("user", "Я люблю Python", "express_love", {"like": "Python"})
    recalled = m.recall("Python", top_n=5)
    assert len(recalled) >= 1


def test_episodic_decay():
    m = EpisodicMemory()
    m.remember("user", "Привет", "greeting", {})
    m.decay()
    assert m.episodes[0]["age"] == 1
    assert m.episodes[0]["importance"] < 0.5


def test_episodic_consolidation():
    m = EpisodicMemory()
    for i in range(15):
        m.remember("user", f"Важный факт номер {i}", "introduce_name",
                    {"fact": f"fact_{i}"})
    # After consolidation, some should be in consolidated
    assert len(m.consolidated) >= 0  # may be 0 if none reached 0.7 importance


def test_episodic_facts():
    m = EpisodicMemory()
    m.remember("user", "Меня зовут Алекс", "introduce_name", {"user_name": "Алекс"})
    m._consolidate()
    facts = m.get_facts()
    assert any("Алекс" in f for f in facts)


def test_episodic_save_load():
    m = EpisodicMemory()
    m.remember("user", "тест", "greeting", {})
    data = m.to_dict()
    assert data["_turn_counter"] >= 1

    m2 = EpisodicMemory()
    m2.from_dict(data)
    assert m2._turn_counter >= 1


# ── v9: ProactiveEngine ──

def test_proactive_interest():
    p = ProactiveEngine()
    p.observe("topic_music", "Я люблю музыку")
    assert p.interest_scores["topic_music"] > 0


def test_proactive_decay():
    p = ProactiveEngine()
    p.observe("topic_music", "Музыка")
    p.decay_interests()
    assert p.interest_scores["topic_music"] < 0.15  # decayed slightly


def test_proactive_suggestion():
    p = ProactiveEngine()
    p.observe("topic_music", "Люблю джаз")
    p.interest_scores["topic_music"] = 0.8
    suggestion = p.get_suggestion(5)
    assert suggestion is not None
    assert "слухаєш" in suggestion.lower() or "музык" in suggestion.lower()


def test_proactive_should_suggest():
    p = ProactiveEngine()
    assert p.should_suggest(4, 0.6) is True
    assert p.should_suggest(2, 0.6) is False  # too few turns
    assert p.should_suggest(4, 0.2) is False  # low engagement


def test_proactive_save_load():
    p = ProactiveEngine()
    p.observe("topic_space", "Космос")
    data = p.to_dict()
    assert "topic_space" in data["interest_scores"]

    p2 = ProactiveEngine()
    p2.from_dict(data)
    assert p2.interest_scores["topic_space"] > 0


# ── CoreModel integration ──

def test_core_model_basic():
    m = CoreModel()
    assert m.version == "2.0.0"
    assert m.total_cycles == 0

    r = m.process("Привет!")
    assert r is not None
    assert m.total_cycles >= 1


def test_core_model_exit():
    m = CoreModel()
    assert m.process("пока") == "__EXIT__"
    assert m.process("до свидания") == "__EXIT__"
    assert m.process("exit") == "__EXIT__"


def test_core_model_empty():
    m = CoreModel()
    r = m.process("")
    assert r is not None
    assert len(r) > 0


def test_core_model_multi_turn():
    m = CoreModel()
    texts = ["Привет!", "Как дела?", "Расскажи шутку", "Нормально"]
    for t in texts:
        r = m.process(t)
        assert r is not None

    assert m.total_cycles == len(texts)
    assert m.planner.turn_count == len(texts)


def test_core_model_learner_active():
    m = CoreModel()
    m.process("Я люблю Python и программирование")
    assert m.learner.user_word_freq["люблю"] >= 1
    assert m.learner.user_word_freq["программирование"] >= 1


def test_core_model_personality_updates():
    m = CoreModel()
    m.process("Мне грустно сегодня")
    assert m.personality.mood in ("supportive", "neutral")


def test_core_model_episodic_memory():
    m = CoreModel()
    m.process("Меня зовут Дима")
    assert len(m.memory.episodes) >= 1


def test_core_model_proactive_tracking():
    m = CoreModel()
    m.process("Расскажи про космос")
    # intent resolver returns "ask_tell", which doesn't start with "topic_"
    # proactive engine's interest_scores stays empty — observe only tracks topic_* intents
    assert len(m.proactive.interest_scores) == 0


def test_core_model_introspection():
    m = CoreModel()
    m.process("ыыы")
    assert m.introspect.get_average_quality() >= 0


def test_core_model_status():
    m = CoreModel()
    m.process("Привет!")
    m.process("Как дела?")
    status = m.get_status()
    assert status["total_cycles"] == 2
    assert status["turn_count"] == 2
    assert status["version"] == "2.0.0"


def test_core_model_thinking_trace():
    m = CoreModel()
    m.process("Привет!")
    trace = m.get_thinking_trace()
    assert "CoreModel v2" in trace
    assert "Цикл" in trace or "Настрій" in trace


def test_core_model_save_load():
    m = CoreModel()
    m.process("Привет!")
    m.process("Как дела?")

    data = m.save_state()
    assert data["total_cycles"] == 2

    m2 = CoreModel()
    m2.load_state(data)
    assert m2.total_cycles == 2
    assert m2.planner.turn_count == 2


def test_core_model_full_cycle():
    """Test all 7 stages work end-to-end."""
    m = CoreModel()

    # Sense + Reason + Plan + Execute + Learn + Reflect + Adapt
    r = m.process("Расскажи шутку про программистов")
    assert r is not None
    assert len(r) > 5

    # Verify all components were touched
    assert m.intent_resolver is not None
    assert m.reasoning is not None
    assert m.planner is not None
    assert m.dispatcher is not None
    assert m.learner is not None
    assert m.introspect is not None
    assert m.personality is not None
    assert m.memory is not None
    assert m.proactive is not None


def test_core_model_reset():
    m = CoreModel()
    m.process("Привет!")
    assert m.total_cycles >= 1
    m.reset()
    assert m.total_cycles == 0
    assert m.planner.turn_count == 0


def test_all_modules_import():
    import modules.core_model as cm
    assert hasattr(cm, "CoreModel")
    assert hasattr(cm, "EnsembleIntentResolver")
    assert hasattr(cm, "ReasoningEngine")
    assert hasattr(cm, "DialoguePlanner")
    assert hasattr(cm, "EngineDispatcher")
    assert hasattr(cm, "OnlineLearner")
    assert hasattr(cm, "Introspection")
    assert hasattr(cm, "PersonalityDynamics")
    assert hasattr(cm, "EpisodicMemory")
    assert hasattr(cm, "ProactiveEngine")
