import os
import re
import shlex
import subprocess

from collections import namedtuple
from itertools import chain

from ..action import ReportAction
from ..config import buttoncombo

ReportAction.add_option("--bindings", metavar="bindings",
                        help="Use custom action bindings specified in the "
                             "config file")

ReportAction.add_option("--profile-toggle", metavar="button(s)",
                        type=buttoncombo("+"),
                        help="A button combo that will trigger profile "
                             "cycling, e.g. 'R1+L1+PS'")

ActionBinding = namedtuple("ActionBinding", "modifiers button callback args")


class ReportActionBinding(ReportAction):
    """Listens for button presses and executes actions."""

    actions = {}

    @classmethod
    def action(cls, name):
        def decorator(func):
            cls.actions[name] = func
            return func

        return decorator

    def __init__(self, controller):
        super(ReportActionBinding, self).__init__(controller)

        self.bindings = []
        self.active = set()

    def add_binding(self, combo, callback, *args):
        modifiers, button = combo[:-1], combo[-1]
        binding = ActionBinding(modifiers, button, callback, args)
        self.bindings.append(binding)

    def load_options(self, options):
        self.active = set()
        self.bindings = []

        bindings = (self.controller.bindings["global"].items(),
                    self.controller.bindings.get(options.bindings, {}).items())

        for binding, action in chain(*bindings):
            self.add_binding(binding, self.handle_binding_action, action)

        have_profiles = (self.controller.profiles and
                         len(self.controller.profiles) > 1)
        if have_profiles and self.controller.default_profile.profile_toggle:
            self.add_binding(self.controller.default_profile.profile_toggle,
                             lambda r: self.controller.next_profile())

    def handle_binding_action(self, report, action):
        info = dict(name=self.controller.device.name,
                    profile=self.controller.current_profile,
                    device_addr=self.controller.device.device_addr,
                    report=report)

        def replace_var(match):
            var, attr = match.group("var", "attr")
            var = info.get(var)
            if attr:
                var = getattr(var, attr, None)
            return str(var)

        action = re.sub(r"\$(?P<var>\w+)(\.(?P<attr>\w+))?",
                        replace_var, action)
        action_split = shlex.split(action)
        action_type = action_split[0]
        action_args = action_split[1:]

        func = self.actions.get(action_type)
        if func:
            try:
                func(self.controller, *action_args)
            except Exception as err:
                self.logger.error("Failed to execute action: {0}", err)
        else:
            self.logger.error("Invalid action type: {0}", action_type)

    def handle_report(self, report):
        for binding in self.bindings:
            modifiers = True
            for button in binding.modifiers:
                modifiers = modifiers and getattr(report, button)

            active = getattr(report, binding.button)
            released = not active

            if modifiers and active and binding not in self.active:
                self.active.add(binding)
            elif released and binding in self.active:
                self.active.remove(binding)
                binding.callback(report, *binding.args)


@ReportActionBinding.action("exec")
def exec_(controller, cmd, *args):
    """Executes a subprocess in the foreground, blocking until returned."""
    controller.logger.info("Executing: {0} {1}", cmd, " ".join(args))

    try:
        subprocess.check_call([cmd] + list(args))
    except (OSError, subprocess.CalledProcessError) as err:
        controller.logger.error("Failed to execute process: {0}", err)


@ReportActionBinding.action("exec-background")
def exec_background(controller, cmd, *args):
    """Executes a subprocess in the background."""
    controller.logger.info("Executing in the background: {0} {1}",
                           cmd, " ".join(args))

    try:
        subprocess.Popen([cmd] + list(args),
                         stdout=open(os.devnull, "wb"),
                         stderr=open(os.devnull, "wb"))
    except OSError as err:
        controller.logger.error("Failed to execute process: {0}", err)


@ReportActionBinding.action("next-profile")
def next_profile(controller):
    """Loads the next profile."""
    controller.next_profile()


@ReportActionBinding.action("prev-profile")
def prev_profile(controller):
    """Loads the previous profile."""
    controller.prev_profile()


@ReportActionBinding.action("load-profile")
def load_profile(controller, profile):
    """Loads the specified profile."""
    controller.load_profile(profile)
