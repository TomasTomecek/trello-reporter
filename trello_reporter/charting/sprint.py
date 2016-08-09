"""
logic for sprints
"""

import logging

from django.core.exceptions import ObjectDoesNotExist


logger = logging.getLogger(__name__)


def find_sprints_by_completed(lists):
    """
    find sprints based on "Completed" list, whenever there are 0 cards, it means that sprint ended
    and a new one is starting

    :return:
    """
    sprints = []
    current_count = 0

    history = {}  # date -> ("+" or "-", ca)

    for li in lists:
        for ca in li.card_actions.order_by("date"):
            history[ca.date] = ("+", ca)
            try:
                na = ca.next_action
            except ObjectDoesNotExist:
                pass
            else:
                history[na.date] = ("-", na)
    logger.debug("len(history) = %s", len(history))
    for da in sorted(history.keys()):
        event_type, _ = history[da]
        if event_type == "+":
            current_count += 1
        elif event_type == "-":
            current_count -= 1
        logger.debug("%d %s", current_count, da)
        if current_count == 0:
            try:
                sprints[-1]["end_dt"] = da
            except IndexError:
                pass
            sprint = {
                "start_dt": da,
                "end_dt": None,
            }
            sprints.append(sprint)
            logger.debug(sprint)
    return sprints
