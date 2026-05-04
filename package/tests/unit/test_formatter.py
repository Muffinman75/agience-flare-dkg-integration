"""Unit tests for agience_dkg_integration formatter."""

from agience_dkg_integration.formatter import artifact_to_markdown, session_uri_for_collection


def test_artifact_to_markdown_contains_required_fields():
    md = artifact_to_markdown(
        title="Architecture Decision: use DKG v10",
        artifact_type="decision",
        artifact_id="art-001",
        content="We will use DKG v10 Working Memory as the shared knowledge substrate.",
        author="Manoj",
        tags=["architecture", "dkg"],
        collection_id="col-1",
    )
    assert "**Agience Artifact:** Architecture Decision: use DKG v10" in md
    assert "**Type:** decision" in md
    assert "**ID:** art-001" in md
    assert "**Author:** Manoj" in md
    assert "**Tags:** architecture, dkg" in md
    assert "**Collection:** col-1" in md
    assert "We will use DKG v10 Working Memory" in md


def test_artifact_to_markdown_optional_fields_omitted_when_absent():
    md = artifact_to_markdown(
        title="Note",
        artifact_type="research-note",
        artifact_id="art-002",
        content="Body",
    )
    assert "**Author:**" not in md
    assert "**Tags:**" not in md
    assert "**Source:**" not in md
    assert "**Collection:**" not in md


def test_artifact_to_markdown_includes_source_url():
    md = artifact_to_markdown(
        title="Note",
        artifact_type="research-note",
        artifact_id="art-003",
        content="Body",
        source_url="https://example.com/doc",
    )
    assert "**Source:** https://example.com/doc" in md


def test_artifact_to_markdown_extra_fields():
    md = artifact_to_markdown(
        title="Note",
        artifact_type="claim",
        artifact_id="art-004",
        content="Body",
        extra_fields={"Confidence": "high", "Domain": "AI safety"},
    )
    assert "**Confidence:** high" in md
    assert "**Domain:** AI safety" in md


def test_session_uri_for_collection_default_base():
    uri = session_uri_for_collection("col-abc")
    assert uri == "agience://collections/col-abc"


def test_session_uri_for_collection_custom_base():
    uri = session_uri_for_collection("col-abc", base_uri="https://agience.ai/collections")
    assert uri == "https://agience.ai/collections/col-abc"
