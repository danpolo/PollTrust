import pytest
from polltrust.ingestion import merge_polls
from polltrust.schemas import ValidationError

def test_invalid_incoming_does_not_mutate_existing():
    existing={"last_successful_update":"2026-01-01T00:00:00Z","polls":[]}
    with pytest.raises(ValidationError): merge_polls(existing,[{"pollster":"p","date":"2026-01-02","source":"https://example.com","parties":{"a":1}}],{"p"})
    assert existing["polls"]==[]

def test_duplicate_is_ignored():
    poll={"pollster":"p","date":"2026-01-01","source":"https://example.com","parties":{"a":60,"b":60}}
    merged,added=merge_polls({"polls":[poll]},[poll],{"p"})
    assert added==0 and len(merged["polls"])==1
