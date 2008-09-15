import appstate

state = appstate.DistributedState()
state.join('YourName+MessageOfTheDayForMyGreatApp')
print state['message']
# Do the rest of MyGreatApp
