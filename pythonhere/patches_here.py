"""Monkey patching Kivy @('_')@."""

from kivy.factory import Factory
from kivy.lang.builder import BuilderBase
import kivy.uix.widget


_original_factory_register = Factory.register
_original_builderbase_match = BuilderBase.match
# pylint: disable=protected-access
_original_widget_destructor = kivy.uix.widget._widget_destructor


def _patched_factory_register(classname, *args, **kwargs):
    """Register a new classname, even if it was already registered."""
    if classname in Factory.classes:
        Factory.classes.pop(classname)
    return _original_factory_register(classname, *args, **kwargs)


def _patched_builderbase_match(self, widget):
    """Return a list of rules matching the widget,
    with no duplicates for rules created with the `%there kv`.
    """
    rules = _original_builderbase_match(self, widget)
    pythonhere_rules = {
        rule.name: rule for rule in rules if (rule.ctx.filename or "").isdigit()
    }
    if pythonhere_rules:
        rules = [
            rule for rule in rules if not (rule.ctx.filename or "").isdigit()
        ] + list(pythonhere_rules.values())
    return rules


def _patched_widget_destructor(*args, **kwargs):
    """Internal method called when a widget is deleted from memory.
    Call the original method, and ignore KeyError
    when uid is not found in `_widget_destructors`.
    """
    try:
        return _original_widget_destructor(*args, **kwargs)
    except KeyError:
        pass


def monkeypatch_kivy():
    """Apply patches to Kivy classes."""
    Factory.register = _patched_factory_register  # pylint: disable=assigning-non-slot
    BuilderBase.match = _patched_builderbase_match
    kivy.uix.widget._widget_destructor = _patched_widget_destructor
