from ivcap_service.config import Config, DEF_OUT_DIR
from ivcap_service.cio import FileAdapter

#from ivcap_service.src.ivcap_service.config import DEF_OUT_DIR

def test_count_words():
    """Test reading Config."""
    cfg = Config([])
    assert type(cfg.IO_ADAPTER) == FileAdapter
    assert cfg.IO_ADAPTER.out_dir == '.'
