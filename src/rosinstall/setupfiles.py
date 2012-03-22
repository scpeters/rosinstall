# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function

import os

from helpers import ROSInstallException, get_ros_stack_path, get_ros_package_path, ROSINSTALL_FILENAME
from config_elements import SetupConfigElement

CATKIN_CMAKE_TOPLEVEL="""#
#  TOPLEVEL cmakelists
#
cmake_minimum_required(VERSION 2.8)
cmake_policy(SET CMP0003 NEW)
cmake_policy(SET CMP0011 NEW)

set(CMAKE_CXX_FLAGS_INIT "-Wall")

enable_testing()

include(${CMAKE_SOURCE_DIR}/workspace-config.cmake OPTIONAL)

list(APPEND CMAKE_PREFIX_PATH ${CMAKE_BINARY_DIR} ${CMAKE_BINARY_DIR}/cmake)

file(MAKE_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
file(MAKE_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

if (IS_DIRECTORY ${CMAKE_SOURCE_DIR}/catkin)
  message(STATUS "+++ catkin")
  set(CATKIN_BUILD_PROJECTS "ALL" CACHE STRING
    "List of projects to build, or ALL for all.  Use to completely exclude certain projects from cmake traversal.")
  add_subdirectory(catkin)
else()
  find_package(catkin)
endif()

catkin_workspace()
"""

def generate_catkin_cmake(path, catkinpp):
    with open(os.path.join(path, "CMakeLists.txt"), 'w') as cmake_file:
      cmake_file.write(CATKIN_CMAKE_TOPLEVEL)

    if catkinpp:
      with open(os.path.join(path, "workspace-config.cmake"), 'w') as config_file:
        config_file.write("set (CMAKE_PREFIX_PATH %s)"%catkinpp)

def generate_setup_sh_text(workspacepath):
  # overlay or standard
  text =  """#!/usr/bin/env sh
# THIS IS A FILE AUTO-GENERATED BY rosinstall
# IT IS UNLIKELY YOU WANT TO EDIT THIS FILE BY HAND
# IF YOU WANT TO CHANGE THE ROS ENVIRONMENT VARIABLES
# USE THE rosinstall OR rosws TOOL INSTEAD.
# see: http://www.ros.org/wiki/rosinstall
"""
# Sadly we cannot infer the workspacepath from within the sourced file
  text += """\nexport ROS_WORKSPACE=%s
if [ ! "$ROS_MASTER_URI" ] ; then export ROS_MASTER_URI=http://localhost:11311 ; fi
unset ROS_ROOT
""" % workspacepath
   
# use python script to read ros_package_path and setup-file elements
  text += """
# python script to read .rosinstall even when rosnistall is not installed
export _PARSED_CONFIG=`/usr/bin/env python << EOPYTHON
import sys, os, yaml;
filename = '.rosinstall'
if 'ROS_WORKSPACE' in os.environ:
  filename = os.path.join(os.environ['ROS_WORKSPACE'], filename)
if not os.path.isfile(filename):
    sys.exit("There is no file at %s"%filename)
with open(filename, "r") as f:
  try:
    v=f.read();
  except Exception as e:
    sys.exit("Failed to read file: %s %s "%(filename, str(e)))
try:
  y = yaml.load(v);
except Exception as e:
  sys.exit("Invalid yaml in %s: %s "%(filename, str(e)))
if y is not None:
  lnames=[x.values()[0]['local-name'] for x in y if x.values() is not None and x.keys()[0] != "setup-file"]
  paths = [os.path.normpath(os.path.join(os.environ['ROS_WORKSPACE'], z)) for z in lnames if not os.path.isfile(os.path.join(os.environ['ROS_WORKSPACE'], z))]
  output=''
  if len(paths) > 0:
    output += ':'.join(reversed(paths))
  output += 'ROSINSTALL_PATH_SETUPFILE_SEPARATOR'
  snames=[x.values()[0]['local-name'] for x in y if x.values() is not None and x.keys()[0] == "setup-file"]
  paths = [os.path.join(os.environ['ROS_WORKSPACE'], z) for z in snames if os.path.isfile(os.path.join(os.environ['ROS_WORKSPACE'], z))]
  output += ':'.join(paths)
  print(output)
EOPYTHON`

#whitespace separates results
_ROS_PACKAGE_PATH_ROSINSTALL=`echo "$_PARSED_CONFIG" | sed -s 's,\(.*\)ROSINSTALL_PATH_SETUPFILE_SEPARATOR\(.*\),\\1,'`
_SETUPFILES_ROSINSTALL=`echo "$_PARSED_CONFIG" | sed -s 's,\(.*\)'ROSINSTALL_PATH_SETUPFILE_SEPARATOR'\(.*\),\\2,'`
unset _PARSED_CONFIG

# colon separates entries
_LOOP_SETUP_FILE=`echo $_SETUPFILES_ROSINSTALL | sed -s 's,\([^:]*\)[:]\(.*\),\\1,'`
while [ ! -z "$_LOOP_SETUP_FILE" ]
do
  if [ -f "$_LOOP_SETUP_FILE" ]; then
    . $_LOOP_SETUP_FILE
  else
    echo warn: no such file : "$_LOOP_SETUP_FILE"
  fi
  _SETUPFILES_ROSINSTALL=`echo $_SETUPFILES_ROSINSTALL | sed -s 's,\([^:]*[:]*\),,'`
  _LOOP_SETUP_FILE=`echo $_SETUPFILES_ROSINSTALL | sed -s 's,\([^:]*\)[:]\(.*\),\\1,'`
done

unset _LOOP_SETUP_FILE
unset _SETUPFILES_ROSINSTALL

export ROS_PACKAGE_PATH=$_ROS_PACKAGE_PATH_ROSINSTALL
unset _ROS_PACKAGE_PATH_ROSINSTALL

# using ROS_ROOT now being in ROS_PACKAGE_PATH
export _ROS_ROOT_ROSINSTALL=`/usr/bin/env python << EOPYTHON
import sys, os;
if 'ROS_PACKAGE_PATH' in os.environ:
  pkg_path = os.environ['ROS_PACKAGE_PATH']
  for path in pkg_path.split(':'):
    if (os.path.basename(path) == 'ros'
        and os.path.isfile(os.path.join(path, 'stack.xml'))):
      print(path)
      break
EOPYTHON`
if [ ! -z "${_ROS_ROOT_ROSINSTALL}" ]; then
  export ROS_ROOT=$_ROS_ROOT_ROSINSTALL
  export PATH=$ROS_ROOT/bin:$PATH
  export PYTHONPATH=$ROS_ROOT/core/roslib/src:$PYTHONPATH
fi
unset _ROS_ROOT_ROSINSTALL
"""

  return text

def generate_setup_bash_text(shell, no_ros = False):
  if shell == 'bash':
    script_path = """
SCRIPT_PATH="${BASH_SOURCE[0]}";
if([ -h "${SCRIPT_PATH}" ]) then
  while([ -h "${SCRIPT_PATH}" ]) do SCRIPT_PATH=`readlink "${SCRIPT_PATH}"`; done
fi
export OLDPWDBAK=$OLDPWD
pushd . > /dev/null
cd `dirname ${SCRIPT_PATH}` > /dev/null
SCRIPT_PATH=`pwd`;
popd  > /dev/null
export OLDPWD=$OLDPWDBAK
"""
  elif shell == 'zsh':
    script_path = 'SCRIPT_PATH="$(dirname $0)"';
  else:
    raise ROSInstallException("%s shell unsupported."%shell);

  text =  """#!/usr/bin/env %(shell)s
# THIS IS A FILE AUTO-GENERATED BY rosinstall
# IT IS UNLIKELY YOU WANT TO EDIT THIS FILE BY HAND
# IF YOU WANT TO CHANGE THE ROS ENVIRONMENT VARIABLES
# USE THE rosinstall TOOL INSTEAD.
# see: http://www.ros.org/wiki/rosinstall

CATKIN_SHELL=%(shell)s

%(script_path)s

# Load the path of this particular setup.%(shell)s

if [ ! -f "$SCRIPT_PATH/setup.sh" ]; then
  echo "Bug: shell script unable to determine its own location: $SCRIPT_PATH"
  return 22
fi


# unset _ros_decode_path to check later whether setup.sh has sourced ros%(shell)s
unset -f _ros_decode_path 1> /dev/null 2>&1

. $SCRIPT_PATH/setup.sh"""%locals()

  if not no_ros:
    text += """
# Cannot rely on $? due to set -o errexit in build scripts
RETURNCODE=`type _ros_decode_path 2> /dev/null | grep function 1>/dev/null 2>&1 || echo error`

if [ ! "$RETURNCODE" = "" ]; then
  RETURNCODE=`rospack help 1> /dev/null 2>&1 || echo error`
  if  [ "$RETURNCODE" = "" ]; then
    ROSSHELL_PATH=`rospack find rosbash`/rosbash
    if [ -e "$ROSSHELL_PATH" ]; then
      . $ROSSHELL_PATH
    fi
  else
    echo "rospack could not be found, you cannot have ros%(shell)s features until you bootstrap ros"
  fi
fi
"""%locals()
  return text


def generate_setup(config, no_ros_allowed = False):
  ros_root = get_ros_stack_path(config)
  if not ros_root:
    if not no_ros_allowed:
      raise ROSInstallException("""
No 'ros' stack detected in candidates %s.
Please add the location of a ros distribution to this command.

See http://ros.org/wiki/rosinstall."""%([t.get_path() for t in config.get_config_elements() if os.path.basename(t.get_local_name())=='ros']) )
  
  text = generate_setup_sh_text(workspacepath = config.get_base_path())
  setup_path = os.path.join(config.get_base_path(), 'setup.sh')
  with open(setup_path, 'w') as f:
    f.write(text)


  for shell in ['bash', 'zsh']:
    text = generate_setup_bash_text(shell, ros_root is None)
    setup_path = os.path.join(config.get_base_path(), 'setup.%s'%shell)
    with open(setup_path, 'w') as f:
      f.write(text)


