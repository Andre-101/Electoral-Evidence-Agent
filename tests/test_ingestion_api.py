from pathlib import Path
import pytest
from tests.conftest import get_test_client
@pytest.mark.integration
def test_ingestion_profile_map_flow():
    client=get_test_client(); sample=Path("data/samples/sample_presidential_table_level.csv")
    with sample.open('rb') as fh:
        r=client.post('/ingestions', data={'source_name':'test_sample','execution_mode':'EXPLORATORY'}, files={'file':('sample.csv', fh, 'text/csv')})
    payload=r.json(); assert r.status_code==200; assert payload['success'] is True
    rid=payload['data']['ingestion_run_id']
    p=client.post(f'/ingestions/{rid}/profile').json(); assert p['success'] is True; assert p['data']['detected_format']=='CSV'
    m=client.post(f'/ingestions/{rid}/map', json={}).json(); assert m['success'] is True; assert m['data']['analysis_level_candidate']=='TABLE_LEVEL'
