"""Where the guardrail ids come from.

Baking an id into a systemd unit meant rotating a guardrail silently left the deployment on
the old version with nothing to tell you. These pin the resolution order that replaced it:
an explicit environment variable wins, Parameter Store is the fallback, and neither being
present is not an error — it just means no guardrail.
"""

from unittest.mock import patch

import pytest

from app.ai import config


@pytest.fixture(autouse=True)
def clean():
    """settings() and _parameters() are both cached for the process; tests need them fresh."""
    config.settings.cache_clear()
    config._parameters.cache_clear()
    yield
    config.settings.cache_clear()
    config._parameters.cache_clear()


def with_params(values: dict[str, str]):
    return patch.object(config, "_parameters", lambda: values)


def test_parameter_store_supplies_the_ids_when_nothing_is_exported(monkeypatch):
    for name in ("BEDROCK_GUARDRAIL_ID", "BEDROCK_GUARDRAIL_VERSION",
                 "BEDROCK_TEACHER_GUARDRAIL_ID", "BEDROCK_TEACHER_GUARDRAIL_VERSION"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DEMO_OFFLINE", "0")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")

    with with_params({"guardrail_id": "fam-1", "guardrail_version": "4",
                      "teacher_guardrail_id": "tea-1", "teacher_guardrail_version": "2"}):
        current = config.settings()
    assert current.guardrail == {"guardrailIdentifier": "fam-1", "guardrailVersion": "4"}
    assert current.teacher_guardrail == {"guardrailIdentifier": "tea-1", "guardrailVersion": "2"}


def test_an_exported_value_beats_parameter_store(monkeypatch):
    monkeypatch.setenv("BEDROCK_GUARDRAIL_ID", "from-env")
    monkeypatch.setenv("BEDROCK_GUARDRAIL_VERSION", "9")
    monkeypatch.setenv("DEMO_OFFLINE", "0")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")

    with with_params({"guardrail_id": "from-ssm", "guardrail_version": "4"}):
        current = config.settings()
    assert current.guardrail == {"guardrailIdentifier": "from-env", "guardrailVersion": "9"}


def test_no_parameters_and_no_environment_means_no_guardrail(monkeypatch):
    for name in ("BEDROCK_GUARDRAIL_ID", "BEDROCK_TEACHER_GUARDRAIL_ID"):
        monkeypatch.delenv(name, raising=False)
    with with_params({}):
        current = config.settings()
    assert current.guardrail is None
    assert current.teacher_guardrail is None


def test_parameter_store_being_unreachable_is_not_fatal(monkeypatch):
    """A laptop with no AWS must still start. The lookup fails closed to an empty dict."""
    monkeypatch.delenv("BEDROCK_GUARDRAIL_ID", raising=False)
    with patch("boto3.client", side_effect=RuntimeError("no credentials")):
        assert config._parameters() == {}


def test_a_teacher_guardrail_alone_never_loosens_the_family_one(monkeypatch):
    """If only the teacher id resolves, family text must not silently inherit the laxer
    policy — it gets none, and the pipeline runs unguarded rather than wrongly guarded."""
    for name in ("BEDROCK_GUARDRAIL_ID", "BEDROCK_TEACHER_GUARDRAIL_ID"):
        monkeypatch.delenv(name, raising=False)
    with with_params({"teacher_guardrail_id": "tea-1", "teacher_guardrail_version": "2"}):
        current = config.settings()
    assert current.guardrail is None
    assert current.teacher_guardrail == {"guardrailIdentifier": "tea-1", "guardrailVersion": "2"}
