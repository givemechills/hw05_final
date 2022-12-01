from django.utils import timezone

now = timezone.now()


def year(request):
    return {
        year: timezone.now()
    }
