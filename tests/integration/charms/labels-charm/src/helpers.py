import re


def compare_secret_ids(secret_id1: str, secret_id2: str) -> bool:
    """Reliable comparison on secret equality.
    Taken from existing PR where we're targeting this problem

    NOTE: Secret IDs may be of any of these forms:
     - secret://9663a790-7828-4186-8b21-2624c58b6cfe/citb87nubg2s766pab40
     - secret:citb87nubg2s766pab40
    """
    if not secret_id1 or not secret_id2:
        return False

    regex = re.compile(".*[^/][/:]")

    pure_id1 = regex.sub("", secret_id1)
    pure_id2 = regex.sub("", secret_id2)

    if pure_id1 and pure_id2:
        return pure_id1 == pure_id2
    return False
