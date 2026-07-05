import string, secrets

def generate_short_code(length=6):
    base62_chars = string.ascii_letters + string.digits
    short_code = ''.join(secrets.choice(base62_chars) for _ in range(length))

    return short_code

