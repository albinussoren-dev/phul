def test_text_limit():
 from backend.services.file_service import validate_text_size
 assert len(validate_text_size("x"*60000))==50000