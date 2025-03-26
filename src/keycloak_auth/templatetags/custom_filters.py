from datetime import datetime

from django import template

register = template.Library()


@register.filter
def unix_to_datetime(value):
    try:
        return datetime.fromtimestamp(int(value))
    except (ValueError, TypeError):
        return ""


# This can be moved wherever it is more appropriate.
@register.filter
def in_any_group(user, group_names):
    """
    Template filter to check if a user belongs to any of the given groups.
    Usage: `if user|in_any_group:"group1,group2,group3`
    """
    if not user.is_authenticated:
        return False
    group_list = [group.strip() for group in group_names.split(",")]
    return user.groups.filter(name__in=group_list).exists()
