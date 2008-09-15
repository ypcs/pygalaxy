import appstate

state = appstate.DistributedState()
state.join('YourName+CounterTest')

def inc(x):
    return x + 1

state.apply_op('count', inc, create=True, defaultvalue=1)
print state['count']
