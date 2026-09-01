from collections import OrderedDict

from django.db.models import Count
from django.http import JsonResponse

from tsosi.models import Entity


def stats_view(request):
    """
    View to return some stats on tsosi_types.
    """

    stats = list(
        Entity.objects.filter(is_active=True)
        .values("tsosi_type")
        .annotate(count=Count("tsosi_type"))
        .order_by("tsosi_type")
    )
    tsosi_type = OrderedDict(
        [(stat["tsosi_type"], stat["count"]) for i, stat in enumerate(stats)]
    )
    stats = list(
        Entity.objects.filter(tsosi_type="other")
        .values("ror_types")
        .annotate(count=Count("ror_types"))
        .order_by("ror_types")
    )
    other_ror_types = OrderedDict(
        [
            (str(stat["ror_types"]), stat["count"])
            for stat in stats
            if stat["ror_types"] is not None
        ]
    )
    return JsonResponse(
        {
            "tsosi_type": tsosi_type,
            "other_ror_types": other_ror_types,
        },
        safe=False,
    )


# tsosi_type : {
#     "company": 22,
#     "funder": 16,
# },
# other_ror_types :
