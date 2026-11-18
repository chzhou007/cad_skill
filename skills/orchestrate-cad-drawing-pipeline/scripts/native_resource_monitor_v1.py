import argparse,json,time
from pathlib import Path
import psutil

def main():
    p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--stop',type=Path,required=True);a=p.parse_args();parent=psutil.Process(a.pid);own=psutil.Process();prior={};samples=[];previous=time.monotonic();psutil.cpu_percent()
    while not a.stop.exists()and parent.is_running():
        time.sleep(.35);now=time.monotonic();delta=0;memory=0;count=0
        try:processes=[parent]+parent.children(recursive=True)
        except psutil.Error:break
        for proc in processes:
            if proc.pid==own.pid:continue
            try:
                key=(proc.pid,proc.create_time());cpu=proc.cpu_times();value=cpu.user+cpu.system;memory+=proc.memory_info().rss;count+=1
                if key in prior:delta+=max(0,value-prior[key])
                prior[key]=value
            except psutil.Error:pass
        samples.append(dict(system_cpu_percent=psutil.cpu_percent(),job_busy_cores=round(delta/max(.001,now-previous),2),job_processes=count,sum_RSS_GB=round(memory/2**30,3)));previous=now
    report=dict(logical_processors=psutil.cpu_count(),peak_system_CPU_percent=max((s['system_cpu_percent']for s in samples),default=0),peak_job_busy_cores=max((s['job_busy_cores']for s in samples),default=0),peak_sum_RSS_GB=max((s['sum_RSS_GB']for s in samples),default=0),samples=samples)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
