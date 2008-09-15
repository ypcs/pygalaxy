import appstate

state = appstate.DistributedState()
state.login('your@email', 'password')
state.new_app('YourName+CounterTest', appstate.ANY, appstate.ANY)
