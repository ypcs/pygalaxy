/*
Python bindings for fluidsynth
Version 1.1
by Nathan Whitehead, (c) 2008

Released under the LGPL
*/

#include <Python.h>
#include <fluidsynth.h>
#include <stdlib.h>

fluid_settings_t* settings = NULL;
fluid_synth_t* synth = NULL;
fluid_audio_driver_t* adriver = NULL;


static PyObject *
pyfluidsynth_version(PyObject *self, PyObject *args)
{
    /* This is the API version of the bindings */
    /* Version 1 - just had start(), did the work of init automatically */
    /* Version 2 - you do init() then optionally start() */
    return Py_BuildValue("i", 2);
}

static PyObject *
pyfluidsynth_init(PyObject *self, PyObject *args)
{
    /* Create the settings. */
    settings = new_fluid_settings();
    
    /* Change the settings if necessary*/
    
    /* Create the synthesizer. */
    synth = new_fluid_synth(settings);
    
    return Py_BuildValue("i", 1);
}

static PyObject *
pyfluidsynth_start(PyObject *self, PyObject *args)
{
    /* Create the audio driver. The synthesizer starts playing as soon
       as the driver is created. */
    adriver = new_fluid_audio_driver(settings, synth);
    
    return Py_BuildValue("i", 1);
}

static PyObject *
pyfluidsynth_stop(PyObject *self, PyObject *args)
{
    /* Clean up */
    if(adriver) delete_fluid_audio_driver(adriver);
    if(synth) delete_fluid_synth(synth);
    if(settings) delete_fluid_settings(settings);
    return Py_BuildValue("i", 1);
}

static PyObject *
pyfluidsynth_sfload(PyObject *self, PyObject *args)
{
    char *fn;
    int sfont_id;
    /* Parse filename */
    if (!PyArg_ParseTuple(args, "s", &fn))
        return NULL;
    /* Load a SoundFont*/
    sfont_id = fluid_synth_sfload(synth, fn, 0);
    return Py_BuildValue("i", sfont_id);
}

static PyObject *
pyfluidsynth_program_select(PyObject *self, PyObject *args)
{
    int chan, sfid, bank, preset, res;
    /* Parse integers */
    if (!PyArg_ParseTuple(args, "iiii", &chan, &sfid, &bank, &preset))
        return NULL;
    res = fluid_synth_program_select(synth, chan, sfid, bank, preset);
    return Py_BuildValue("i", res);
}

static PyObject *
pyfluidsynth_noteon(PyObject *self, PyObject *args)
{
    int chan, key, vel, res;
    /* Parse integers */
    if (!PyArg_ParseTuple(args, "iii", &chan, &key, &vel))
        return NULL;
    res = fluid_synth_noteon(synth, chan, key, vel);
    return Py_BuildValue("i", res);
}

static PyObject *
pyfluidsynth_noteoff(PyObject *self, PyObject *args)
{
    int chan, key, res;
    /* Parse integers */
    if (!PyArg_ParseTuple(args, "ii", &chan, &key))
        return NULL;
    res = fluid_synth_noteoff(synth, chan, key);
    return Py_BuildValue("i", res);
}

static PyObject *
pyfluidsynth_pitch_bend(PyObject *self, PyObject *args)
{
    int chan, val, res;
    /* Parse integers */
    if (!PyArg_ParseTuple(args, "ii", &chan, &val))
        return NULL;
    res = fluid_synth_pitch_bend(synth, chan, val);
    return Py_BuildValue("i", res);
}

static PyObject *
pyfluidsynth_cc(PyObject *self, PyObject *args)
{
    int chan, ctrl, val, res;
    /* Parse integers */
    if (!PyArg_ParseTuple(args, "iii", &chan, &ctrl, &val))
        return NULL;
    res = fluid_synth_cc(synth, chan, ctrl, val);
    return Py_BuildValue("i", res);
}

static PyObject *
pyfluidsynth_program_change(PyObject *self, PyObject *args)
{
    int chan, prg, res;
    /* Parse integers */
    if (!PyArg_ParseTuple(args, "ii", &chan, &prg))
        return NULL;
    res = fluid_synth_program_change(synth, chan, prg);
    return Py_BuildValue("i", res);
}

static PyObject *
pyfluidsynth_bank_select(PyObject *self, PyObject *args)
{
    int chan, bank, res;
    /* Parse integers */
    if (!PyArg_ParseTuple(args, "ii", &chan, &bank))
        return NULL;
    res = fluid_synth_bank_select(synth, chan, bank);
    return Py_BuildValue("i", res);
}

static PyObject *
pyfluidsynth_sfont_select(PyObject *self, PyObject *args)
{
    int chan, sfid, res;
    /* Parse integers */
    if (!PyArg_ParseTuple(args, "ii", &chan, &sfid))
        return NULL;
    res = fluid_synth_sfont_select(synth, chan, sfid);
    return Py_BuildValue("i", res);
}

static PyObject *
pyfluidsynth_program_reset(PyObject *self, PyObject *args)
{
    int res;
    res = fluid_synth_program_reset(synth);
    return Py_BuildValue("i", res);
}

static PyObject *
pyfluidsynth_system_reset(PyObject *self, PyObject *args)
{
    int res;
    res = fluid_synth_system_reset(synth);
    return Py_BuildValue("i", res);
}

static PyObject *
pyfluidsynth_write_s16(PyObject *self, PyObject *args)
{
    int len;
    char *buf;
    /* Parse integers */
    if (!PyArg_ParseTuple(args, "i", &len))
        return NULL;
    /* len is the number of frames to write */
    /* each frame is 2 bytes * 2 channels = 4 bytes */
    buf = malloc(len * 4);
    fluid_synth_write_s16(synth, len, buf, 0, 2, buf, 1, 2);
    return Py_BuildValue("s#", buf, len * 4);
}

static PyMethodDef PyfluidsynthMethods[] = {
    { "version", pyfluidsynth_version, METH_VARARGS, "API version number."},
    { "init", pyfluidsynth_init, METH_VARARGS, "Init fluidsynth."},
    { "start", pyfluidsynth_start, METH_VARARGS, "Start fluidsynth audio driver."},
    { "stop", pyfluidsynth_stop, METH_VARARGS, "Stop fluidsynth."},
    { "sfload", pyfluidsynth_sfload, METH_VARARGS, "Load soundfont."},
    { "program_select", pyfluidsynth_program_select, METH_VARARGS, "Select program."},
    { "noteon", pyfluidsynth_noteon, METH_VARARGS, "Start note."},
    { "noteoff", pyfluidsynth_noteoff, METH_VARARGS, "Stop note."},
    { "pitch_bend", pyfluidsynth_pitch_bend, METH_VARARGS, "Pitch bend."},
    { "cc", pyfluidsynth_cc, METH_VARARGS, "Control change."},
    { "program_change", pyfluidsynth_program_change, METH_VARARGS, "Program change."},
    { "bank_select", pyfluidsynth_bank_select, METH_VARARGS, "Bank select."},
    { "sfont_select", pyfluidsynth_sfont_select, METH_VARARGS, "SoundFont select."},
    { "program_reset", pyfluidsynth_program_reset, METH_VARARGS, "Program reset."},
    { "system_reset", pyfluidsynth_system_reset, METH_VARARGS, "System reset."},
    { "write_s16", pyfluidsynth_write_s16, METH_VARARGS, "Get samples."},
    { NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initpyfluidsynth(void)
{
    (void)Py_InitModule("pyfluidsynth", PyfluidsynthMethods);
}

