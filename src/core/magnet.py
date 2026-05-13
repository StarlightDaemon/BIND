from urllib.parse import quote_plus


def generate_magnet(info_hash: str, title: str, trackers: list[str]) -> str:
    """
    Generates a robust magnet link with trackers.
    Title is URL-encoded to handle special characters (&, +, =, ?, #, spaces, etc.)
    """
    # URL-encode title to prevent broken links when title contains special characters
    # quote_plus() encodes spaces as '+' and special chars as '%XX'
    title_encoded = quote_plus(title)

    magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={title_encoded}"
    for tr in trackers:
        magnet += f"&tr={tr}"
    return magnet
