import pygments
import pygments.lexers
import pygments.formatters

def highlight(text, lexer_name='py', fmt='html', noclasses=True, style=None, lineanchors='l'):
    text = str(text)
    formatter_options = { "lineanchors" : lineanchors, "noclasses" : noclasses }
    if style is not None:
        formatter_options['style'] = style
    lexer = pygments.lexers.get_lexer_by_name(lexer_name)
    formatter = pygments.formatters.get_formatter_by_name(fmt, **formatter_options)
    return pygments.highlight(text, lexer, formatter)
