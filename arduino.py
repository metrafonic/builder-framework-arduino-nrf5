# Copyright 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Arduino

Arduino Wiring-based Framework allows writing cross-platform software to
control devices attached to a wide range of Arduino boards to create all
kinds of creative coding, interactive objects, spaces or physical experiences.
"""

from os import listdir
from os.path import isdir, join

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()

FRAMEWORK_DIR = platform.get_package_dir("framework-arduinonordicnrf5")
FRAMEWORK_VERSION = platform.get_package_version("framework-arduinonordicnrf5")
assert isdir(FRAMEWORK_DIR)

env.Append(
    CFLAGS=["-std=gnu11"],

    CCFLAGS=["--param", "max-inline-insns-single=500"],

    CXXFLAGS=[
        "-std=gnu++11",
        "-fno-threadsafe-statics"
    ],

    CPPDEFINES=[
        # For compatibility with sketches designed for AVR@16 MHz (see SPI lib)
        ("F_CPU", "16000000L"),
        "ARDUINO_ARCH_NRF5",
        "NRF5"
    ],

    LIBPATH=[
        join(FRAMEWORK_DIR, "cores",
             env.BoardConfig().get("build.core"), "SDK", "components",
             "toolchain", "gcc")
    ],

    CPPPATH=[
        join(FRAMEWORK_DIR, "cores", env.BoardConfig().get("build.core")),
        join(FRAMEWORK_DIR, "cores",
             env.BoardConfig().get("build.core"), "SDK", "components",
             "drivers_nrf", "delay"),
        join(FRAMEWORK_DIR, "cores",
             env.BoardConfig().get("build.core"), "SDK", "components",
             "device"),
        join(FRAMEWORK_DIR, "cores",
             env.BoardConfig().get("build.core"), "SDK", "components",
             "toolchain"),
        join(FRAMEWORK_DIR, "cores",
             env.BoardConfig().get("build.core"), "SDK", "components",
             "toolchain", "CMSIS", "Include")
    ],

    LINKFLAGS=[
        "--specs=nano.specs",
        "--specs=nosys.specs",
        "-Wl,--check-sections",
        "-Wl,--unresolved-symbols=report-all",
        "-Wl,--warn-common",
        "-Wl,--warn-section-align"
    ],

    LIBSOURCE_DIRS=[join(FRAMEWORK_DIR, "libraries")])

if env.BoardConfig().get("build.cpu") == "cortex-m4":
    env.Append(
        CCFLAGS=[
            "-mfloat-abi=softfp",
            "-mfpu=fpv4-sp-d16"
        ]
    )

env.Append(
    CPPDEFINES=["%s" % env.BoardConfig().get("build.mcu", "")[0:5].upper()]
)

# Process softdevice options
softdevice_ver = ""
cpp_defines = env.Flatten(env.get("CPPDEFINES", []))
if "NRF52_S132" in cpp_defines:
    softdevice_ver = "s132"
elif "NRF51_S130" in cpp_defines:
    softdevice_ver = "s130"
elif "NRF51_S110" in cpp_defines:
    softdevice_ver = "s110"

if softdevice_ver:

    env.Append(
        CPPPATH=[
            join(FRAMEWORK_DIR, "cores", env.BoardConfig().get("build.core"),
            "SDK", "components", "softdevice", softdevice_ver, "headers")
        ],

        CPPDEFINES=["%s" % softdevice_ver.upper()]
    )

    hex_path = join(FRAMEWORK_DIR, "cores",
                    env.BoardConfig().get("build.core"), "SDK", "components",
                    "softdevice", softdevice_ver, "hex")

    for f in listdir(hex_path):
        if f.endswith(".hex") and f.lower().startswith(softdevice_ver):
            env.Append(SOFTDEVICEHEX=join(hex_path, f))

    if "SOFTDEVICEHEX" not in env:
        print "Warning! Cannot find an appropriate softdevice binary!"

    # Update linker script:
    ldscript_dir = join(FRAMEWORK_DIR, "cores",
                        env.BoardConfig().get("build.core"), "SDK",
                        "components", "softdevice", softdevice_ver,
                        "toolchain", "armgcc")
    mcu_family = env.BoardConfig().get("build.ldscript", "").split("_")[1]
    ldscript_path = ""
    for f in listdir(ldscript_dir):
        if f.endswith(mcu_family) and softdevice_ver in f.lower():
            ldscript_path = join(ldscript_dir, f)

    if ldscript_path:
        env.Replace(LDSCRIPT_PATH=ldscript_path)
    else:
        print("Warning! Cannot find an appropriate linker script for the "
              "required softdevice!")

# Select crystal oscillator as the low frequency source by default
clock_options = ("USE_LFXO", "USE_LFRC" "USE_LFSYNT")
if not any(d in clock_options for d in cpp_defines):
    env.Append(CPPDEFINES=["USE_LFXO"])

# Construct upload flags
upload_args = []
upload_protocol = env.subst("$UPLOAD_PROTOCOL")
debug_tools = env.BoardConfig().get("debug.tools", {})
if upload_protocol in debug_tools:
    upload_args = ["-s", platform.get_package_dir("tool-openocd") or ""]
    upload_args += debug_tools.get(
        upload_protocol).get("server").get("arguments", [])
    upload_args += ["-c", "program {{$SOURCE}} verify reset; shutdown;"]
else:
    print "Warning! Cannot find an apropriate upload method!"

env.Replace(
    LIBS=["m"],
    UPLOADER="openocd",
    UPLOADERFLAGS=upload_args,
    UPLOADCMD='"$UPLOADER" $UPLOADERFLAGS'
)

#
# Target: Build Core Library
#

libs = []

if "build.variant" in env.BoardConfig():
    env.Append(CPPPATH=[
        join(FRAMEWORK_DIR, "variants", env.BoardConfig().get("build.variant"))
    ])

    libs.append(
        env.BuildLibrary(
            join("$BUILD_DIR", "FrameworkArduinoVariant"),
            join(FRAMEWORK_DIR, "variants",
                 env.BoardConfig().get("build.variant"))))

libs.append(
    env.BuildLibrary(
        join("$BUILD_DIR", "FrameworkArduino"),
        join(FRAMEWORK_DIR, "cores", env.BoardConfig().get("build.core"))))

env.Prepend(LIBS=libs)