from collections import OrderedDict

from django.db.models import Count, Max
from django.http import JsonResponse
from django.views.decorators.cache import cache_page

from tsosi.models import DataLoadSource, Entity, Transfer


def stats_view(request):
    """
    View to return some stats on tsosi_types.
    """

    stats = list(
        Entity.objects.public()
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

@cache_page(60 * 15)
def home_figures_view(request):
    """
    Key figures of the home page
    """
    transfers = Transfer.objects.filter(
        merged_into__isnull=True, is_future=False
    )
    amount_usd = sum(
        (amounts or {}).get("USD") or 0
        for amounts in transfers.values_list("amounts_clc", flat=True)
    )
    date_data_update = DataLoadSource.objects.aggregate(
        date=Max("date_data_obtained")
    )["date"]
    return JsonResponse(
        {
            "supports": transfers.count(),
            "amount_usd": round(amount_usd),
            "date_data_update": date_data_update,
        }
    )
