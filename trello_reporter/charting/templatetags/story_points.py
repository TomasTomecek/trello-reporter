from django import template

from trello_reporter.charting.models import Card, CardAction

register = template.Library()


@register.simple_tag
def sum_story_points(array):
    """ sum story points on a given array, acceptable items are Card, CardAction"""
    if array:
        if isinstance(array[0], Card):
            return sum([c.latest_action.story_points for c in array])
        elif isinstance(array[0], CardAction):
            return sum([ca.story_points for ca in array])
