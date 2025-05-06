from django.db import models


class ApiRequest(models.Model):
    """
    Abstract model logging the performed API requests.
    TODO: Also log the request URL ?
    """

    # Useful information for debugging, usually the request's URL or
    # the query for the SPARQL queries.
    info = models.TextField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True, null=False)
    http_status = models.IntegerField(null=True)
    error = models.BooleanField(default=False, null=False)
    error_msg = models.TextField(null=True)

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=(
                    (models.Q(error=False) & models.Q(error_msg__isnull=True))
                    | (models.Q(error=True) & models.Q(error_msg__isnull=False))
                ),
                name="%(app_label)s_%(class)s_request_error_msg_when_failed",
            )
        ]
