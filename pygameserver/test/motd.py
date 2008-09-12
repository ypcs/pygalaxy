import appstate

appstate.init('testing+motd')
motd = appstate.get_state()
print motd
# now do rest of application
