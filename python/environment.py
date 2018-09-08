global_env_default = "builtin"


global_env = "notset"
global_set = False


def builtin():
    import socket
    from threading import Thread, Event, Lock
    from subprocess import Popen
    import subprocess
    from time import sleep

    env = {}
    env["socket"] = socket
    env["Event"] = Event

    def spawn(target, *args, **kwargs):
        t = Thread(target=target, *args, **kwargs)
        t.daemon = True
        t.start()
        return t

    env["spawn"] = spawn
    env["Lock"] = Lock
    env["subprocess"] = subprocess
    env["Popen"] = Popen
    env["sleep"] = sleep
    return env


def gevent():
    from gevent import socket, Event, Lock
    from gevent import sleep, spawn
    from gevent.subprocess import Popen
    import subprocess

    env = {}
    env["socket"] = socket
    env["Event"] = Event

    def spawn(target, *args, **kwargs):
        t = spawn(target, *args, **kwargs)
        return t

    env["spawn"] = spawn
    env["Lock"] = Lock
    env["subprocess"] = subprocess
    env["Popen"] = Popen
    env["sleep"] = sleep
    return env


def get_env(*args):
    global global_env, global_set
    if not global_set:
        global_env = global_env_default
        global_set = True
    env = globals()[global_env]()
    if len(args) == 1:
        return env.get(args[0])
    return [env.get(x) for x in args]


def set_env(env):
    global global_env, global_set
    if global_set:
        raise RuntimeError("Environment already set")
    global_set = True
    global_env = env
