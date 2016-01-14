PyGalaxy is an open source library of useful functions that make creating 2D games in pygame easier.  A sampling of features:
  * graphics primitives
  * load transparent and animated GIFs correctly
  * framerate utilities
  * sprite engine with many features
  * dynamic music mixing (music heats up with more enemies)
  * microphone input and pitch detection
  * simple physics engine
  * AI functions such as pathfinding and state machines
  * interface with Wii Remote, use all the features of the WiiMote in your game

Some of the pieces of PyGalaxy are packaged separately for independent use.  These include:
  * [SWMixer](SWMixer.md) - software mixer that allows precise sample control and simultaneous microphone input while playing
  * [pyFluidSynth](pyFluidSynth.md) - bindings for FluidSynth, a software MIDI synthesizer that uses SoundFonts (SF2 files) for instruments
  * [SoundAnalyse](SoundAnalyse.md) - real-time pitch detection algorithms coded in C, and other sound analysis functions
  * [AppState](AppState.md) - connection to Google App Engine for persistent shared distributed state, use for high scores, sharing custom levels in game, etc.