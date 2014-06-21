import inspect
import re
import collections
from cloudbot.event import EventType

valid_command_re = re.compile(r"^\w+$")


class _Hook():
    """
    :type function: function
    :type type: str
    :type kwargs: dict[str, unknown]
    """

    def __init__(self, function, _type):
        """
        :type function: function
        :type _type: str
        """
        self.function = function
        self.type = _type
        self.kwargs = {}

    def _add_hook(self, **kwargs):
        """
        :type kwargs: dict[str, unknown]
        """
        # update kwargs, overwriting duplicates
        self.kwargs.update(kwargs)


class _CommandHook(_Hook):
    """
    :type main_alias: str
    :type aliases: set[str]
    """

    def __init__(self, function):
        """
        :type function: function
        """
        _Hook.__init__(self, function, "command")
        self.aliases = set()
        self.main_alias = None

        if function.__doc__:
            self.doc = function.__doc__.split('\n', 1)[0]
        else:
            self.doc = None

    def add_hook(self, *aliases, **kwargs):
        """
        :type aliases: list[str] | str
        """
        self._add_hook(**kwargs)

        if not aliases:
            aliases = [self.function.__name__]
        elif len(aliases) == 1 and not isinstance(aliases[0], str):
            # we are being passed a list as the first argument, so aliases is in the form of ([item1, item2])
            aliases = aliases[0]

        if not self.main_alias:
            self.main_alias = aliases[0]

        for alias in aliases:
            if not valid_command_re.match(alias):
                raise ValueError("Invalid command name {}".format(alias))
        self.aliases.update(aliases)


class _RegexHook(_Hook):
    """
    :type regexes: list[re.__Regex]
    """

    def __init__(self, function):
        """
        :type function: function
        """
        _Hook.__init__(self, function, "regex")
        self.regexes = []

    def add_hook(self, *regexes, **kwargs):
        """
        :type regexes: Iterable[str | re.__Regex] | str | re.__Regex
        :type kwargs: dict[str, unknown]
        """
        self._add_hook(**kwargs)

        # If we have one argument, and that argument is neither a string or a compiled regex, we're being passed a list
        if len(regexes) == 1 and not (isinstance(regexes[0], str) or hasattr(regexes[0], "search")):
            regexes = regexes[0]  # it's a list we're being passed as the first argument, so take it as a list

        assert isinstance(regexes, collections.Iterable)
        # if the parameter is a list, add each one
        for re_to_match in regexes:
            if isinstance(re_to_match, str):
                re_to_match = re.compile(re_to_match)
            # make sure that the param is either a compiled regex, or has a search attribute.
            assert hasattr(re_to_match, "search")
            self.regexes.append(re_to_match)


class _RawHook(_Hook):
    """
    :type triggers: set[str]
    """

    def __init__(self, function):
        """
        :type function: function
        """
        _Hook.__init__(self, function, "irc_raw")
        self.triggers = set()

    def add_hook(self, *triggers, **kwargs):
        """
        :type triggers: list[str] | str
        :type kwargs: dict[str, unknown]
        """
        self._add_hook(**kwargs)
        if len(triggers) == 1 and not isinstance(triggers[0], str):
            # we are being passed a list as the first argument, so triggers is in the form of ([item1, item2])
            triggers = triggers[0]

        self.triggers.update(triggers)


class _EventHook(_Hook):
    """
    :type types: set[cloudbot.event.EventType]
    """

    def __init__(self, function):
        """
        :type function: function
        """
        _Hook.__init__(self, function, "event")
        self.types = set()

    def add_hook(self, *events, **kwargs):
        """
        :type events: tuple[cloudbot.event.EventType] | (list[cloudbot.event.EventType])
        :type kwargs: dict[str, unknown]
        """
        self._add_hook(**kwargs)

        if len(events) == 1 and not isinstance(events[0], EventType):
            # we are being passed a list as the first argument, so events is in the form of ([item1, item2])
            events = events[0]

        self.types.update(events)


def _add_hook(func, hook):
    if not hasattr(func, "_cloudbot_hook"):
        func._cloudbot_hook = {}
    else:
        assert hook.type not in func._cloudbot_hook  # in this case the hook should be using the add_hook method
    func._cloudbot_hook[hook.type] = hook


def _get_hook(func, hook_type):
    if hasattr(func, "_cloudbot_hook") and hook_type in func._cloudbot_hook:
        return func._cloudbot_hook[hook_type]

    return None


def command(*aliases, **kwargs):
    """External command decorator. Can be used directly as a decorator, or with args to return a decorator.
    :type param: tuple[str] | (list[str]) | (function)
    """

    def decorator(func):
        hook = _get_hook(func, "command")
        if hook is None:
            hook = _CommandHook(func)
            _add_hook(func, hook)
        if len(aliases) == 1 and callable(aliases[0]):
            hook.add_hook(**kwargs)  # we don't want to pass the function as an argument
        else:
            hook.add_hook(*aliases, **kwargs)
        return func

    if len(aliases) == 1 and callable(aliases[0]):  # this decorator is being used directly
        return decorator(aliases[0])
    else:  # this decorator is being used indirectly, so return a decorator function
        return decorator


def irc_raw(*triggers, **kwargs):
    """External raw decorator. Must be used as a function to return a decorator
    :type triggers: tuple[str] | (list[str])
    """

    def decorator(func):
        hook = _get_hook(func, "irc_raw")
        if hook is None:
            hook = _RawHook(func)
            _add_hook(func, hook)

        hook.add_hook(*triggers, **kwargs)
        return func

    if len(triggers) == 1 and callable(triggers[0]):  # this decorator is being used directly, which isn't good
        raise TypeError("irc_raw() must be used as a function that returns a decorator")
    else:  # this decorator is being used as a function, so return a decorator
        return decorator


def event(*triggers, **kwargs):
    """External event decorator. Must be used as a function to return a decorator
    :type triggers: tuple[cloudbot.event.EventType] | (list[cloudbot.event.EventType])
    """

    def decorator(func):
        hook = _get_hook(func, "event")
        if hook is None:
            hook = _EventHook(func)
            _add_hook(func, hook)

        hook.add_hook(*triggers, **kwargs)
        return func

    if len(triggers) == 1 and callable(triggers[0]):  # this decorator is being used directly, which isn't good
        raise TypeError("event() must be used as a function that returns a decorator")
    else:  # this decorator is being used as a function, so return a decorator
        return decorator


def regex(*regexes, **kwargs):
    """External regex decorator. Must be used as a function to return a decorator.
    :type regexes: tuple[str | re.__Regex] | (list[str | re.__Regex])
    :type flags: int
    """

    def decorator(func):
        hook = _get_hook(func, "regex")
        if hook is None:
            hook = _RegexHook(func)
            _add_hook(func, hook)

        hook.add_hook(*regexes, **kwargs)
        return func

    if len(regexes) == 1 and callable(regexes[0]):  # this decorator is being used directly, which isn't good
        raise TypeError("regex() hook must be used as a function that returns a decorator")
    else:  # this decorator is being used as a function, so return a decorator
        return decorator


def sieve(param=None, **kwargs):
    """External sieve decorator. Can be used directly as a decorator, or with args to return a decorator
    :type param: function | None
    """

    def decorator(func):
        assert len(inspect.getargspec(func).args) == 3, \
            "Sieve plugin has incorrect argument count. Needs params: bot, input, plugin"

        hook = _get_hook(func, "sieve")
        if hook is None:
            hook = _Hook(func, "sieve")  # there's no need to have a specific SieveHook object
            _add_hook(func, hook)

        hook._add_hook(**kwargs)
        return func

    if callable(param):
        return decorator(param)
    else:
        return decorator


def onload(param=None, **kwargs):
    """External onload decorator. Can be used directly as a decorator, or with args to return a decorator
    :type param: function | None
    """

    def decorator(func):
        hook = _get_hook(func, "onload")
        if hook is None:
            hook = _Hook(func, "onload")
            _add_hook(func, hook)

        hook._add_hook(**kwargs)
        return func

    if callable(param):
        return decorator(param)
    else:
        return decorator
