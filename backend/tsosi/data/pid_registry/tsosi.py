import random
import string

from tsosi.models import Identifier

TSOSI_ID_REGEX = r"^T[0-9]{6+}$"
REGISTRY_TSOSI = "tsosi"


def generate_tsosi_id():
    """
    Generate a new random TSOSI ID.
    """
    existing_ids = set(
        Identifier.objects.filter(registry_id=REGISTRY_TSOSI).values_list(
            "value", flat=True
        )
    )
    while True:
        new_id = "T" + "".join(random.choices(string.digits, k=6))
        if new_id not in existing_ids:
            return new_id
