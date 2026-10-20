from django import template

register = template.Library()


@register.simple_tag
def split_messages(messages):
    '''Pisahkan pesan popup dari pesan toast reguler.'''
    items = list(messages)
    return {
        'popup': [
            message for message in items
            if {'account_created', 'popup'} & set((message.extra_tags or '').split())
        ],
        'toast': [
            message for message in items
            if not {'account_created', 'popup'} & set((message.extra_tags or '').split())
        ],
    }
