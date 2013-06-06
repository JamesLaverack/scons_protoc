""" 
protoc.py: Protoc Builder for SCons

This Builder invokes protoc to generate C++ and Python 
from a .proto file.  

Original author: Scott Stafford

Modifed by Steven Haywood (steven.haywood.2010@my.bristol.ac.uk) for:
1) Java support
2) Single-project multiple protoc output langauges support via neat* interface

Note these changes break perfect backwards compatability. A simple change
of "env.Protoc(target.cpp, source.proto)" to "env.ProtocCPP(target, source)"
is all that is required. (similarly for Python). Note the environment variable
wrangling previously required to select output language is replaced with
explicit language builders and is therefore no longer required.

*: REMOVING the environment variable for the language you DO NOT want is,
in my (Steven Haywood's) opinion, NOT neat.

"""

__author__ = "Scott Stafford"

import SCons.Action
import SCons.Builder
import SCons.Defaults
import SCons.Node.FS
import SCons.Util

from SCons.Script import File, Dir

import os.path

protocs = 'protoc'

ProtocJavaAction = SCons.Action.Action(
						'$PROTOCCOM_START $PROTOCJAVAFLAG $PROTOCCOM_END', 
						'Running protoc for Java output')
						
ProtocPythonAction = SCons.Action.Action(
						'$PROTOCCOM_START $PROTOCPYTHONFLAG $PROTOCCOM_END', 
						'Running protoc for Python output')
						
ProtocCPPAction = SCons.Action.Action(
						'$PROTOCCOM_START $PROTOCCPPFLAG $PROTOCCOM_END', 
						'Running protoc for CPP output')

def _ProtocEmitter(target, source, env, output_lang):
    """
    Generlised emitter function for protoc commands.
    
    output_lang must be one of 'java', 'python', 'cpp'
    """
    
    dirOfCallingSConscript = Dir('.').srcnode()
    
    env.Prepend(PROTOCPROTOPATH = dirOfCallingSConscript.path)
    
    source_with_corrected_path = []
    
    for src in source:
        commonprefix = os.path.commonprefix([dirOfCallingSConscript.path, 
        									 src.srcnode().path])
        
        if len(commonprefix) > 0:
            source_with_corrected_path.append( 
            				src.srcnode().path[len(commonprefix + os.sep):] )
        else:
            source_with_corrected_path.append( src.srcnode().path )
        
    source = source_with_corrected_path
    
    for src in source:
        modulename = os.path.splitext(src)[0]

        if output_lang == 'cpp':            
            base = os.path.join(env['PROTOCOUTDIR'] , modulename)
            target.extend( [ base + '.pb.cc', base + '.pb.h' ] )
        elif output_lang == 'python':
            base = os.path.join(env['PROTOCPYTHONOUTDIR'] , modulename)
            target.append( base + '_pb2.py' )
        elif output_lang == 'java':
            base = os.path.join(env['PROTOCJAVAOUTDIR'] , modulename)
            target.append( base + '_pb2.java' )

    try:
        target.append(env['PROTOCFDSOUT'])
    except KeyError:
        pass
        
    #~ print "PROTOC SOURCE:", [str(s) for s in source]
    #~ print "PROTOC TARGET:", [str(s) for s in target]

    return target, source

def ProtocJavaEmitter(target, source, env):
	# Use generalised emitter:
	return _ProtocEmitter(target, source, env, 'java')
	
def ProtocPythonEmitter(target, source, env):
	return _ProtocEmitter(target, source, env, 'python')
	
def ProtocCPPEmitter(target, source, env):
	return _ProtocEmitter(target, source, env, 'cpp')

# Define the three language builders:
ProtocJavaBuilder = SCons.Builder.Builder(action = ProtocJavaAction,
                                   emitter = ProtocJavaEmitter,
                                   srcsuffix = '$PROTOCSRCSUFFIX')

ProtocPythonBuilder = SCons.Builder.Builder(action = ProtocPythonAction,
                                   emitter = ProtocPythonEmitter,
                                   srcsuffix = '$PROTOCSRCSUFFIX')

ProtocCPPBuilder = SCons.Builder.Builder(action = ProtocCPPAction,
                                   emitter = ProtocCPPEmitter,
                                   srcsuffix = '$PROTOCSRCSUFFIX')

_builder_dict = {'ProtocCPP': ProtocCPPBuilder,
                 'ProtocPython': ProtocPythonBuilder,
                 'ProtocJava': ProtocJavaBuilder}

def generate(env):
    """
    Add Builders and construction variables for protoc to an Environment.
    """
    
    for key in _builder_dict.keys():
        try:
            bld = env['BUILDERS'][key]
            #~ print "Found {0} in env['BUILDERS'] already!".format(str(key))
        except KeyError:
            bld = _builder_dict[key]
            env['BUILDERS'][key] = bld
            #~ print "Added {0} to env['BUILDERS']".format(str(key))
        
    env['PROTOC']        = env.Detect(protocs) or 'protoc'
    env['PROTOCFLAGS']   = SCons.Util.CLVar('')
    env['PROTOCPROTOPATH'] = SCons.Util.CLVar('')
    
    # Need to insert an option into the middle of the command,
    # so use start and end COM strings    
    env['PROTOCCOM_START']     = """$PROTOC ${["-I%s"%x for x in PROTOCPROTOPATH]} $PROTOCFLAGS ${PROTOCFDSOUT and ("-o"+PROTOCFDSOUT) or ""}"""
    
    env['PROTOCCOM_END'] = '${SOURCES}'
    
    # Provide environment variables for each possible language output
    # so that users can easily put java files in a different directory
    # to python files etc. Leave the python and CPP defaults as they were
    # previously. Java outputs should probably go in a 'java' directory.
    env['PROTOCOUTDIR'] = '${SOURCE.dir}'
    env['PROTOCPYTHONOUTDIR'] = 'python'
    env['PROTOCJAVAOUTDIR'] = 'java'
    
    # The variable protoc option, provided so that if users wish to alter
    # flags for a specific output language for their project, they can.
    # Obviously, the base --<lang>_out=<dir> part needs to remain.    
    env['PROTOCJAVAFLAG'] = '--java_out=${PROTOCJAVAOUTDIR}'
    env['PROTOCPYTHONFLAG'] = '--python_out=${PROTOCPYTHONOUTDIR}'
    env['PROTOCCPPFLAG'] = '--cpp_out=${PROTOCOUTDIR}'
        
    env['PROTOCSRCSUFFIX']  = '.proto'

def exists(env):
    return env.Detect(protocs)
