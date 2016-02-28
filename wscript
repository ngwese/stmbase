#! /usr/bin/env python
# encoding: utf-8

APPNAME = "ebb"
VERSION = "0.1"

CROSS = "arm-none-eabi-"

top = "."
out = "build"

def options(opt):
    opt.load('gcc')

def configure(ctx):
    ctx.env.BOARD  = "stm32f4xx_nucleo_144"
    ctx.env.CHIP   = "stm32f429xx"
    ctx.env.FAMILY = "stm32f4xx"

    ctx.env.DRIVER_ROOT = "vendor/st/driver/"
    ctx.env.DRIVERS = [
        "cmsis",
        "cmsis/{FAMILY}".format(**ctx.env),
        "hal/{FAMILY}".format(**ctx.env),
        "bsp/{BOARD}".format(**ctx.env)
    ]
    
    ctx.env.STARTUP_CODE = \
        ctx.env.DRIVER_ROOT + "cmsis/{FAMILY}/src/template/startup_{CHIP}.s".format(**ctx.env)
        
    ctx.find_program('openocd', var='OPENOCD')

    # cross-compiler
    ctx.env.CROSS = CROSS
    ctx.env.CC    = ctx.env.CROSS + 'gcc'
    ctx.env.CXX   = ctx.env.CROSS + 'g++'
    ctx.env.AR    = ctx.env.CROSS + 'ar'
    ctx.env.AS    = ctx.env.CROSS + 'as'

    ctx.load('gcc')
    ctx.load('g++')
    ctx.load('gas')

    ctx.find_program(ctx.env.CROSS + 'objcopy', var='OBJCOPY')
    ctx.find_program(ctx.env.CROSS + 'size',    var='SIZE')

    # arm-none-eabi-gcc --print-multi-lib
    # TODO: check flags.
    ctx.env.ARCHFLAGS = [
        '-mcpu=cortex-m4', '-mthumb', #'-mthumb-interwork',
        '-mfloat-abi=hard', '-mfpu=fpv4-sp-d16', 
    ]

    ctx.env.COMMONFLAGS = [
        # https://answers.launchpad.net/gcc-arm-embedded/+question/224614
        '--specs=nano.specs',
    ]

    ctx.env.ASFLAGS = ctx.env.ARCHFLAGS
    
    ctx.env.CFLAGS = ctx.env.ARCHFLAGS + ctx.env.COMMONFLAGS + [
        '-fmessage-length=0', '-fsigned-char',
        '-ffunction-sections', '-fdata-sections', '-ffreestanding', '-fno-move-loop-invariants',
        '-Wall', '-Wextra',
        # debug?
        '-DOS_USE_TRACE_SEMIHOSTING_DEBUG',
        # part
        '-DSTM32F429xx', '-DUSE_HAL_DRIVER', '-DHSE_VALUE=8000000',
        # ??
        '-DVECT_TAB_SRAM',
    ]

    ctx.env.INCLUDES = driver_includes(ctx) + ['src']

    ctx.env.LDFLAGS = ctx.env.ARCHFLAGS + ctx.env.COMMONFLAGS + [
        '-L{0}'.format(ctx.path.find_dir('ldscripts').abspath()),
        '-T', '{CHIP}_flash.ld'.format(**ctx.env),
        #'-nostartfiles',
        '-Xlinker', '--gc-sections',
        '-Wl,-Map,{0}'.format(_appfile("map")),
    ]

    baseEnv = ctx.env

    # customize for release builds
    #ctx.setenv('release', baseEnv)
    #ctx.env.append_unique('CFLAGS', ['-Os', '-g'])    
    #print("\n//// RELEASE ////\n")
    #print(ctx.env)

    # customize for debug builds
    #ctx.setenv('debug', baseEnv)
    ctx.env.append_unique('CFLAGS', ['-Og', '-g3', '-DDEBUG', '-DUSE_FULL_ASSERT', '-DTRACE'])
    #ctx.env.append_unique('CFLAGS', ['-Og', '-g3', '-DDEBUG'])
    #print("\n//// DEBUG ////\n")
    #print(ctx.env)

    

def build(bld):
    # compile

    driver_objs = driver_targets(bld)

    bld.program(
        source = bld.path.ant_glob('src/*.c'),
        target = _appfile('elf'),
        use    = ' '.join(driver_objs + ['startup'])
    )

    bld(
        source = bld.env.STARTUP_CODE,
        target = 'startup',
    )

    bld(name   = 'objcopy',
        rule   = '${OBJCOPY} -O binary ${SRC} ${TGT}',
        source = _appfile('elf'),
        target = _appfile('bin'),
    )
    
    bld(
        name   = 'size',
        rule   = '${SIZE} --format=berkeley ${SRC}',
        source = _appfile('elf'),
    )



def _appfile(ext):
    return "{appname}-{version}.{ext}".format(appname=APPNAME,
                                              version=VERSION,
                                              ext=ext)

def driver_includes(ctx):
        root = ctx.env.DRIVER_ROOT
        drivers = ctx.env.DRIVERS
        # FIXME: cross platform
        return [root + d + '/include' for d in drivers] 

def driver_targets(bld):
        targets = []
        for d in bld.env.DRIVERS:
                sources = bld.path.ant_glob(bld.env.DRIVER_ROOT + d + '/src/*.c', excl=['**/*template*'])
                target = d.replace('/', '_') + '_objs'  # FIXME: cross platform issues
                bld.objects(source=sources, target=target)
                targets.append(target)
        return targets
                
        
