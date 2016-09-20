from django import template
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

register = template.Library()


def present_card(ca):
    t = '<a href="%s" class="trello-link" target="_blank">#%s</a>' % (
        ca.event.card_url,
        ca.event.card_short_id,
    )
    return t


@register.simple_tag
def display_card(ca):
    """ display card, specified by car action """
    t = "%s %s" % (
        present_card(ca),
        ca.card.name,
    )
    return mark_safe(t)


@register.simple_tag
def display_card_with_detail_link(ca):
    """ display card, specified by car action """
    t = "%s <a href=\"%s\">%s</a>"% (
        present_card(ca),
        reverse("card-detail", args=(ca.card_id, )),
        ca.card.name,
    )
    return mark_safe(t)
