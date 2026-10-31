"""Join owned process CPU counters to same-host native observation intervals."""
SCALE=10_000_000
UNIX_TICKS=621355968000000000


def analyze(report,targets,intervals,native_clock_valid):
    if report['schemaVersion']!=1 or report['source']!='OwnedWindowsProcessCpuTiming' or not report['complete'] \
        or report['truncated'] or report['error'] or report['sampleSeconds']!=.05 or report['maximumSeconds']!=240 or report['maximumSamples']!=5000:
        raise ValueError('Incomplete owned process timing')
    if report['targets']!=targets or not 1<=len(targets)<=3 or report['closedHandleCount']!=len(targets):
        raise ValueError('Process identity or handle closure mismatch')
    roles=[t['role'] for t in targets]
    if len(set(roles))!=len(roles) or len({t['pid'] for t in targets})!=len(roles):raise ValueError('Duplicate target identity')
    for t in targets:
        if t['role'] not in ('Visible','Peer','Server') or type(t['pid']) is not int or t['pid']<=0 \
            or type(t['createdFileTime']) is not int or t['createdFileTime']<=0 or not t['executable']:
            raise ValueError('Invalid target identity')
    rows=report['rows'];cycles=report['cycles']
    cycle_version=report.get('cycleCounterVersion',0)
    if type(cycle_version) is not int or cycle_version not in (0,1):raise ValueError('Unsupported CPU cycle counter version')
    if type(cycles) is not int or not 2<=cycles<=5000 or len(rows)!=cycles*len(targets):raise ValueError('Incomplete CPU sample cycles')
    grouped={role:[] for role in roles};previous_end=0;clock_error=0;query_max=0;separation=0
    for index,row in enumerate(rows):
        if row['role']!=roles[index%len(roles)]:raise ValueError('CPU sample role order changed')
        for key in ('fromCounterNs','toCounterNs','fromUnixNs','toUnixNs','kernel100ns','user100ns'):
            if type(row[key]) is not int or row[key]<0:raise ValueError('Invalid CPU sample counter')
        if cycle_version and (type(row.get('cpuCycles')) is not int or row['cpuCycles']<0):raise ValueError('Invalid CPU cycle count')
        a=row['fromCounterNs'];b=row['toCounterNs']
        if not previous_end<=a<=b:raise ValueError('CPU sample counter moved backwards')
        previous_end=b;query_max=max(query_max,b-a)
        clock_error=max(clock_error,abs((row['toUnixNs']-row['fromUnixNs'])-(b-a)))
        prior=grouped[row['role']]
        if prior:
            old=prior[-1]
            if row['kernel100ns']<old['kernel100ns'] or row['user100ns']<old['user100ns']:raise ValueError('CPU accounting counter moved backwards')
            if cycle_version and row['cpuCycles']<old['cpuCycles']:raise ValueError('CPU cycle counter moved backwards')
            clock_error=max(clock_error,abs((row['fromUnixNs']-old['fromUnixNs'])-(a-old['fromCounterNs'])))
            separation=max(separation,a-old['fromCounterNs'])
        prior.append(row)
    # Also compare distant endpoints; many small steps cannot hide UTC drift.
    clock_error=max(clock_error,abs((rows[-1]['toUnixNs']-rows[0]['fromUnixNs'])-(rows[-1]['toCounterNs']-rows[0]['fromCounterNs'])))
    valid=native_clock_valid and clock_error<50_000_000
    def measure(a,b):
        values={}
        for role,observations in grouped.items():
            inside=[r for r in observations if UNIX_TICKS+r['fromUnixNs']//100>=a and UNIX_TICKS+(r['toUnixNs']+99)//100<=b]
            enough=len(inside)>=2
            kernel=inside[-1]['kernel100ns']-inside[0]['kernel100ns'] if enough else None
            user=inside[-1]['user100ns']-inside[0]['user100ns'] if enough else None
            delta=kernel+user if enough else None
            cpu_cycles=inside[-1]['cpuCycles']-inside[0]['cpuCycles'] if enough and cycle_version else None
            values[role]={'interiorSamples':len(inside),'accountedKernel100ns':kernel,'accountedUser100ns':user,
                'accountedCpuSeconds':delta/SCALE if enough else None,
                'activity':'accountedCpuAdvanced' if enough and delta>0 else 'noAccountedAdvanceObserved' if enough else 'insufficientInteriorSamples',
                'cpuCycleDelta':cpu_cycles,
                'cpuCycleAdvancingPairs':sum(y['cpuCycles']>x['cpuCycles'] for x,y in zip(inside,inside[1:])) if enough and cycle_version else None,
                'accountedCpuAdvancingPairs':sum(y['kernel100ns']+y['user100ns']>x['kernel100ns']+x['user100ns'] for x,y in zip(inside,inside[1:])) if enough else None,
                'cycleActivity':'unavailable' if not cycle_version else 'insufficientInteriorSamples' if not enough else 'cycleCounterAdvanced' if cpu_cycles>0 else 'noCycleAdvanceObserved',
                'measuredFromUtcTicks':UNIX_TICKS+inside[0]['fromUnixNs']//100 if enough else None,
                'measuredToUtcTicks':UNIX_TICKS+(inside[-1]['toUnixNs']+99)//100 if enough else None,
                'counterWindowSeconds':(inside[-1]['toCounterNs']-inside[0]['fromCounterNs'])/1e9 if enough else None,
                'bracketedBySamples':any(UNIX_TICKS+(r['toUnixNs']+99)//100<=a for r in observations) and any(UNIX_TICKS+r['fromUnixNs']//100>=b for r in observations)}
        return values
    joined=[]
    for interval in intervals or []:
        a=interval['fromUtcTicks'];b=interval['toUtcTicks']
        if type(a) is not int or type(b) is not int or not 0<a<b:raise ValueError('Invalid native interval')
        duration=b-a
        joined.append({**interval,'processes':measure(a,b),
            'precedingContext':{'fromUtcTicks':a-duration,'toUtcTicks':a,'processes':measure(a-duration,a)},
            'followingContext':{'fromUtcTicks':b,'toUtcTicks':b+duration,'processes':measure(b,b+duration)}})
    return {'source':report['source'],'clockJoinValid':valid,'maximumClockStepSeconds':clock_error/1e9,
        'cycles':cycles,'cycleCounterVersion':cycle_version,'maximumQuerySeconds':query_max/1e9,'maximumSampleSeparationSeconds':separation/1e9,
        'targets':targets,'intervals':joined if valid else None,
        'limits':['Read-only GetProcessTimes kernel / user accounting, summed across all process threads; not main-thread CPU',
            'Only CPU query brackets entirely inside a native interval contribute; no boundary interpolation',
            'Accounting granularity / delayed updates and observer overhead prevent exact execution-time attribution',
            'A positive counter advance does not identify a thread or root cause; zero does not prove suspension',
            'Parallel threads may accumulate more CPU time than the measured wall-clock window',
            'CPU cycles sum all process threads, are not converted to seconds, and zero still does not prove suspension',
            'Equal-length context windows are nearby CPU comparisons, not proof of normal gameplay or no other stalls',
            'No process or thread suspension, memory access, stack sampling, scheduling or privilege changes']}
