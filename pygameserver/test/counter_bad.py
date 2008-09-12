import appstate

state = appstate.DistributedState('testing+counter')

def incr_count():
    try:
        old = state['count']
        new = old + 1
        state['count'] = new
    except KeyError:
        state['count'] = 1

incr_count()
print state['count']
