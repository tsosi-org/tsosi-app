from collections import OrderedDict

from django.db.models import Count, Max
from django.http import Http404, JsonResponse
from django.views.decorators.cache import cache_page

from tsosi.models import DataLoadSource, Entity, NewsItem, Newsletter, Transfer


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
        Entity.objects.public()
        .filter(tsosi_type="other")
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


def news_view(request):
    """
    The news shown on the home page
    """
    news = [
        {
            "kind": item.kind,
            "title": item.title,
            "text": item.text,
            "url": item.url,
            "date": item.date.isoformat() if item.date else None,
            "image": (
                request.build_absolute_uri(item.image.url)
                if item.image
                else None
            ),
            "image_alt": item.image_alt,
        }
        for item in NewsItem.objects.order_by("position")
    ]
    return JsonResponse(news, safe=False)


def newsletter_data(newsletter: Newsletter) -> dict:
    return {
        "id": newsletter.name,
        "date": newsletter.date.isoformat(),
        "key_points": newsletter.key_points,
    }


def newsletters_view(request):
    """The newsletters, latest first (see `tsosi.data.newsletters`)."""
    return JsonResponse(
        [newsletter_data(n) for n in Newsletter.objects.order_by("-date")],
        safe=False,
    )


def newsletter_view(request, name: str):
    """A newsletter, with the HTML content of its body."""
    try:
        newsletter = Newsletter.objects.get(name=name)
    except Newsletter.DoesNotExist:
        raise Http404()
    return JsonResponse(
        {**newsletter_data(newsletter), "html": newsletter.html}
    )
