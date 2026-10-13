from app.utils.shortener import generate_short_code 

import re

class TestShortener:

    def test_length(self):
        assert len(generate_short_code()) == 6

    def test_isBase62(self):
        assert re.fullmatch(r'[0-9a-zA-Z]+',generate_short_code())

    def test_randomess(self):
        # Generate 100 codes and throw them into a set (sets filter out duplicates)
        generated_codes = {generate_short_code() for _ in range(100)}
    
        # If there were duplicates, the set length would be less than 100
        assert len(generated_codes) == 100
