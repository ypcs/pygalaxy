import appstate

state = appstate.DistributedState()
state.join('YourName+CounterTest')

def incr_count():
    try:
        old = state['count']
        new = old + 1
        oldhash = appstate.hash_value(old)
        state.update('count', oldhash, new)
    except appstate.UpdateFailedError:
        incr_count() # try again
    except KeyError:
        state['count'] = 1

incr_count()
print state['count']
