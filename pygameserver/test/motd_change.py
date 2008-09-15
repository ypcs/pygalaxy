import appstate

state = appstate.DistributedState()
state.login('your@email', 'password')
state.join('YourName+MessageOfTheDayForMyGreatApp')
state['message'] = 'If you liked MyGreatApp, you will love MyGreatestApp' 
