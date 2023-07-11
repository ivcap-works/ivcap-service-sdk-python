from ivcap_sdk_service.config import Config, DEF_OUT_DIR
from ivcap_sdk_service.cio import LocalIOAdapter

#from ivcap_service.src.ivcap_service.config import DEF_OUT_DIR

def test_config():
    """Test reading Config."""
    cfg = Config([])
    assert type(cfg.IO_ADAPTER) == LocalIOAdapter
    #assert cfg.IO_ADAPTER.out_dir == '.'
