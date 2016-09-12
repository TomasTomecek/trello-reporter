from django import template
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def present_list(ca):
    """ present list of the givan card acion: either print state or do a link """
    if ca.is_archived:
        t = "Archived"
    elif ca.is_deleted:
        t = "Deleted"
    else:
        t = "<a href=\"%s\">%s</a>" % (
            reverse('list-detail', args=(ca.list.id, )),
            ca.list.name
        )
    return mark_safe(t)
