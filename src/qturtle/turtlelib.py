import multiprocessing
from PyQt5 import QtWidgets
import time as _time
import functools as _functools


#
# Main Master/Slave classes
#
class _TurtleCtrl:
    """
    Controls a TurtleWindow object that is running on a background multiprocess.
    """

    def __init__(self):
        self.queue = multiprocessing.SimpleQueue()
        self.result_queue = multiprocessing.SimpleQueue()
        self.process = multiprocessing.Process(
            target=_start_and_run_window, args=(self.queue, self.result_queue))
        self.process.start()

    def __call__(self, name, *args, **kwds):
        self.queue.put([name, args, kwds])

    def get(self, name, *args, **kwds):
        self.queue.put(['*' + name, args, kwds])
        while self.result_queue.empty():
            _time.sleep(1e-3)
        return self.result_queue.get()


class _TurtleWindow(QtWidgets.QWidget):
    """
    A turtle window that should run in a background process.
    We cannot use threads since Qt expects that the GUI runs in the main thread.

    It communicates with the main process using a Queue of commands.
    """
    _instance = None

    def __new__(cls, queue=None, rqueue=None):
        if cls._instance is None:
            return super().__new__(cls, queue, rqueue)
        else:
            return cls._instance

    def __init__(self, queue=None, rqueue=None):
        from qturtle.turtlescene import TurtleScene, TurtleView

        super().__init__()
        self._scene = TurtleScene()
        self._view = TurtleView(self._scene)
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.addWidget(self._view)
        self.setMinimumSize(800, 600)
        self._namespace = self._scene.getNamespace()
        self._queue = queue
        self._rqueue = rqueue
        self.startTimer(1000 / 30)

    def timerEvent(self, timer):
        if not self._queue.empty():
            task = self._queue.get()
            self.consume(task)

    def keyPressEvent(self, ev):
        key = ev.key()
        modifiers = ev.modifiers()

    def consume(self, task):
        name, args, kwargs = task
        if name.startswith('*'):
            method = getattr(self._namespace, name[1:])
            self._rqueue.put(method(*args, **kwargs))
        else:
            method = getattr(self._namespace, name)
            method(*args, **kwargs)


def _start_and_run_window(queue, rqueue):
    """Entry point for TurtleWindow subprocess."""

    import sys
    app = QtWidgets.QApplication([])
    window = _TurtleWindow(queue, rqueue)
    window.show()
    sys.exit(app.exec_())


#
# Clean namespace and define turtle commands
#
_turtle_ctrl = _TurtleCtrl()
del multiprocessing, QtWidgets


# Simple commands
def _simple_cmd(name, ns):
    @_functools.wraps(getattr(ns, name))
    def wrapped(*args):
        _turtle_ctrl(name, *args)

    return wrapped


def _get_cmd(name, ns):
    @_functools.wraps(getattr(ns, name))
    def wrapped(*args):
        return _turtle_ctrl.get(name, *args)

    return wrapped


def qturtle_namespace():
    """Return qturtle namespace as a dictionary"""

    from qturtle.turtlenamespace import TurtleNamespaceEnglish as turtle_namespace
    namespace = {}

    for _cmd in [
        # Turtle movement
        'forward', 'backward', 'left', 'right', 'penup', 'pendown', 'goto', 'jumpto',

        # Set turtle state
        'setpos', 'setheading', 'setwidth', 'setcolor', 'setfill',

        # Simulation control
        'speed', 'restart', 'clear', 'turtlehelp',

        # Turtle extras
        'print_image'
    ]:
        namespace[_cmd] = _simple_cmd(_cmd, turtle_namespace)

    # Aliases
    for _alias, _name in turtle_namespace._getaliases().items():
        namespace[_alias] = namespace[_name]

    # State getters
    for _cmd in ['getpos', 'getheading', 'getwidth', 'getcolor', 'getfill', 'isdown']:
        namespace[_cmd] = _get_cmd(_cmd, turtle_namespace)

    return namespace


def pytuga_namespace():
    """Return all drawing related functions from pytuga namespace as a dictionary."""

    from qturtle.turtlenamespace import TurtleNamespace as turtle_namespace
    namespace = {}
    namespace_english = qturtle_namespace()

    for _cmd in [
        # Turtle movement
        'frente', 'trás', 'esquerda', 'direita', 'levantar', 'abaixar', 'ir_para', 'pular_para',

        # Set turtle state
        'definir_posição', 'definir_direção', 'definir_espessura', 'definir_cor_da_linha', 'definir_cor_do_fundo',

        # Simulation control
        'velocidade', 'reiniciar', 'limpar', 'ajuda',

        # Turtle extras
        'imprimir_imagem'
    ]:
        namespace[_cmd] = _simple_cmd(_cmd, turtle_namespace)

    # Aliases
    for _alias, _name in turtle_namespace._getaliases().items():
        namespace[_alias] = namespace.get(_name) or namespace_english[_name]

    # State getters
    for _cmd in ['posição', 'direção', 'espessura', 'cor_da_linha', 'cor_do_fundo', 'desenhando']:
        namespace[_cmd] = _get_cmd(_cmd, turtle_namespace)

    return ns


globals().update(pytuga_namespace())
