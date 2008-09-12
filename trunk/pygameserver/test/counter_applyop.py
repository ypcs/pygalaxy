import appstate

state = appstate.DistributedState('testing+counter2')

def inc(x):
    return x + 1

state.apply_op('count', inc, create=True, defaultvalue=0)
print state['count']
