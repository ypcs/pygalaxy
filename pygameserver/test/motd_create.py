
import appstate

state = appstate.DistributedState()
state.login('your@email', 'password')
state.new_app('YourName+MessageOfTheDayForMyGreatApp', 
              readmode=appstate.ANY,
              writemode=appstate.ADMIN_ONLY)
state['message'] = 'New version of MyGreatApp available today!'
