"""Grounded activity recommendation: retrieval over an approved corpus, a Bedrock Converse
call with tool-use for structured output, validation, and a citation check — behind one
offline switch so the demo never depends on the network."""

from . import config, generate, retrieval, schema  # noqa: F401
