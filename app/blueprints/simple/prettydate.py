import ago


def date(dt):
    return ago.human(dt, precision=1)

