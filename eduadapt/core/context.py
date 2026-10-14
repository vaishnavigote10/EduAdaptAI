from django.conf import settings


def team(request):
    members = [dict(m, initial=m["name"][:1].upper()) for m in settings.TEAM]
    return {"team": members, "team_names": " & ".join(m["name"] for m in members)}
