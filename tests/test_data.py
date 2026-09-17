import json
from pathlib import Path
from polltrust.schemas import validate_poll
ROOT=Path(__file__).resolve().parents[1]

def test_current_poll_file_is_valid():
    election=json.loads((ROOT/'data/election.json').read_text(encoding='utf-8')); current=json.loads((ROOT/'data/current-polls.json').read_text(encoding='utf-8'))
    for poll in current['polls']: validate_poll(poll,set(election['pollsters']))

def test_generated_model_contains_every_active_pollster(tmp_path):
    from polltrust.demo_data import build_demo_raw
    from polltrust.model import build_model
    election=json.loads((ROOT/'data/election.json').read_text(encoding='utf-8')); model=build_model(build_demo_raw())
    assert set(model['pollsters'])==set(election['pollsters'])
