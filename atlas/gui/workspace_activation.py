"""Load hidden workspaces when they first open, not on every Atlas landing.

Every callback that runs on page load adds Dash renderer bookkeeping before the
visible Atlas search can run; with ~110 of them the browser spent 15-25 seconds
of main-thread time on hidden panels. Callbacks for a hidden workspace skip the
landing call and run once, with the current inputs, when that workspace first
opens. Afterwards they respond to their own inputs exactly as before.
"""
from dash import Input, Output, State, callback, dcc, no_update

WORKSPACES = ('inspect', 'notebook', 'research', 'map', 'archive', 'missions')
SECTIONS = ('objects', 'states', 'fossils', 'newspapers', 'units', 'guides', 'projects',
            'minerals', 'radiocarbon', 'dinosaurs', 'packs')
GATES = WORKSPACES + tuple('section-' + name for name in SECTIONS)


def gate_id(name):
    if name not in GATES:
        raise ValueError(f'Unknown workspace: {name}')
    return 'workspace-opened-' + name


def stores():
    return [dcc.Store(id=gate_id(name), storage_type='memory') for name in GATES]


def visible(mode, tool, section):
    """Workspaces shown for these navigation values (the Atlas landing shows none)."""
    shown = {mode} & {'inspect', 'notebook', 'research'}
    if mode == 'resident' and tool in ('map', 'archive', 'missions'):
        shown.add(tool)
    if section in SECTIONS:
        shown.add('section-' + section)
    return shown


@callback(*[Output(gate_id(name), 'data') for name in GATES],
          Input('workflow-mode', 'value'), Input('resident-tool', 'value'), Input('library-section', 'value'),
          *[State(gate_id(name), 'data') for name in GATES])
def open_workspaces(mode, tool, section, *opened):
    shown = visible(mode, tool, section)
    return tuple(True if name in shown and opened_before is not True else no_update
                 for name, opened_before in zip(GATES, opened))


def when_opened(workspaces, *dependencies, **options):
    """Register a hidden-workspace callback: no landing call; run when a listed workspace first opens.

    The decorated function keeps its signature (the gate values are removed),
    and the module-level name stays the original function for direct use.
    """
    names = (workspaces,) if isinstance(workspaces, str) else tuple(workspaces)
    gates = [Input(gate_id(name), 'data') for name in names]

    def register(function):
        def on_open(*values):
            return function(*values[:-len(gates)])
        on_open.__name__, on_open.__qualname__ = function.__name__, function.__qualname__
        on_open.__module__, on_open.__doc__ = function.__module__, function.__doc__
        callback(*dependencies, *gates, prevent_initial_call=True, **options)(on_open)
        return function
    return register
