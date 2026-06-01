from pathlib import Path
from app.ingestion.file_reader import detect_file, read_csv
from app.ingestion.hashing import calculate_sha256
from app.ingestion.profiler import profile_dataframe
from app.core.settings import load_yaml_config
SAMPLE = Path("data/samples/sample_presidential_table_level.csv")
def test_hashing_sample_file(): assert len(calculate_sha256(SAMPLE)) == 64
def test_detect_file_sample_csv():
    d=detect_file(SAMPLE); assert d.detected_format == "CSV"; assert d.detected_separator == ","; assert "departamento" in d.columns
def test_profile_dataframe_candidates():
    df=read_csv(SAMPLE); cfg=load_yaml_config("config/column_aliases.yaml"); aliases={f:c.get('aliases',[]) for f,c in cfg.get('canonical_fields',{}).items()}; profiles=profile_dataframe(df, aliases); cand={p.source_field_name:p.candidate_for for p in profiles}; assert cand['departamento']=='department'; assert cand['municipio']=='municipality'; assert cand['mesa']=='table_number'; assert cand['votos']=='votes'
